"""Rule layer: regex field extraction plus an emergency safety net.

Used in two ways:
  1. As an offline fallback "triager" when no LLM API key is available.
  2. As a safety net on top of ANY model: if emergency keywords fire, urgency is
     escalated to 'emergency'. This is how we bias the system towards high
     recall on emergencies (the costliest error).
"""
import re
from typing import Optional

from .schemas import TriageResult

# ---- emergency patterns (English + Hinglish) ----
EMERGENCY_PATTERNS = [
    r"gas (smell|leak)|smell (of )?gas|hissing",
    r"burning smell|smell of (something )?burning|smoke|\bfire\b",
    r"spark(s|ing)?\b",
    r"burst",
    r"electric (shock|shocks)|shock from|shock when",
    r"flood(ing|ed)?",
    r"stuck (between|in) (floors|lift)|lift stuck",
    r"live wire|hanging .*wire|tar neeche latak|bijli ka tar",
    r"carbon monoxide|co alarm",
    r"water (coming|entering|near) .*(switch|electric|panel)",
    r"someone is being (beaten|hurt)|slapping|worried someone is hurt",
    r"overflowing .*(entering|into) ",
]
_EMERG = re.compile("|".join(EMERGENCY_PATTERNS), re.I)

HIGH_PATTERNS = [
    r"no (power|water|electricity|light)", r"power cut", r"since (morning|yesterday|last night)",
    r"locked out", r"intruder|strangers|unknown person", r"dangerous|slipped|almost fell|nearly fell",
    r"sewage", r"overflow", r"light nahi|pani nahi", r"threaten", r"not cooling",
]
_HIGH = re.compile("|".join(HIGH_PATTERNS), re.I)
LOW_PATTERNS = [r"no hurry|not urgent|whenever|anytime|sometime|when time|jab time", r"\bwhen is\b|\bhow do i\b|receipt|\bnoc\b|copy"]
_LOW = re.compile("|".join(LOW_PATTERNS), re.I)

CATEGORY_KEYWORDS = {
    "plumbing": r"tap|pipe|leak|water|paani|pani|nal |toilet|flush|drain|sink|geyser|tank|sewage|shower|basin|washbasin|seep",
    "electrical": r"power|electric|light|bijli|fan|socket|switch|mcb|wire|ac |inverter|lift|meter|bulb|tube|spark|cctv|fridge",
    "payment_query": r"rent|payment|paid|deposit|receipt|upi|cheque|neft|refund|late fee|instal|maintenance charge|penalty|auto debit|\bgst\b|invoice",
    "noise_complaint": r"noise|shor|music|loud|party|drill|bark|stomp|speaker|hammer|dj\b|shouting|banging",
}

TIME_RE = re.compile(
    r"(since (?:morning|yesterday(?: evening)?|last night|\d+\s?(?:am|pm))|\d{1,2}(?::\d{2})?\s?(?:am|pm)|"
    r"\d+\s?(?:hours?|days?|din)|yesterday|last night|this morning|tonight|midnight|overnight|today|tomorrow|right now)",
    re.I,
)
UNIT_PATTERNS = [
    r"(?:flat|unit|room|apt|apartment)\s*(?:no\.?\s*)?([A-Za-z]?-?\d{1,3}[A-Za-z]?)",
    r"\b([A-Za-z]-\d{2,3})\b",
    r"\b(\d{1,2}(?:st|nd|rd|th) floor|ground floor)\b",
    r"(?:\bin|\bat)\s+(\d{2,3}[A-Za-z]?)\b",
    r"\b(\d{1,2}[A-C])\b",
]


def is_emergency(text: str) -> bool:
    return bool(_EMERG.search(text))


def extract_unit(text: str) -> Optional[str]:
    for p in UNIT_PATTERNS:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    m = re.search(r"\.\s*(\d{2,3}[A-Za-z]?)\s*$", text)  # trailing ". 204"
    return m.group(1) if m else None


def extract_time(text: str) -> Optional[str]:
    m = TIME_RE.search(text)
    return m.group(1).strip() if m else None


def rule_category(text: str) -> str:
    t = text.lower()
    scores = {c: len(re.findall(p, t)) for c, p in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def rule_urgency(text: str) -> str:
    if is_emergency(text):
        return "emergency"
    if _HIGH.search(text):
        return "high"
    if _LOW.search(text):
        return "low"
    return "normal"


def rule_triage(text: str) -> TriageResult:
    from .replies import build_reply, build_task
    r = TriageResult(
        category=rule_category(text), urgency=rule_urgency(text),
        unit=extract_unit(text), time_mentioned=extract_time(text),
        issue=None, source="rules",
    )
    r.tenant_reply, r.manager_task = build_reply(r), build_task(r, text)
    r.needs_human_review = r.urgency in ("emergency", "high")
    return r

"""Shared label sets and the output schema used by every triage approach."""
from dataclasses import dataclass, asdict, field
from typing import Optional

CATEGORIES = ["plumbing", "electrical", "payment_query", "noise_complaint", "general"]
URGENCIES = ["emergency", "high", "normal", "low"]  # ordered most -> least urgent


@dataclass
class TriageResult:
    category: str
    urgency: str
    unit: Optional[str] = None
    issue: Optional[str] = None
    time_mentioned: Optional[str] = None
    tenant_reply: str = ""
    manager_task: str = ""
    needs_human_review: bool = False
    source: str = ""  # which approach produced this result

    def to_dict(self):
        return asdict(self)

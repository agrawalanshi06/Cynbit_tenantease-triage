"""Template replies/tasks (used by the offline fallback only; the LLM writes its own)."""
from .schemas import TriageResult

SLA = {"emergency": "immediately", "high": "within 4 hours", "normal": "within 2 days", "low": "within a week"}


def build_reply(r: TriageResult) -> str:
    unit = f" for unit {r.unit}" if r.unit else ""
    if r.urgency == "emergency":
        return (f"We have received your message{unit} and are treating it as an EMERGENCY. "
                "Please stay safe and keep away from the hazard. Your property manager is being alerted right now. "
                "If anyone is in danger, call the local emergency number (112) immediately.")
    if r.category == "payment_query":
        return f"Thanks for reaching out{unit}. We are checking your payment details and will reply {SLA[r.urgency]}."
    return (f"Thanks for reporting this{unit}. We have logged it as {r.urgency} priority "
            f"and your manager will get back to you {SLA[r.urgency]}.")


def build_task(r: TriageResult, text: str) -> str:
    unit = r.unit or "unit unknown"
    return f"[{r.urgency.upper()}] {r.category} | {unit} | respond {SLA[r.urgency]} | original: {text[:120]}"

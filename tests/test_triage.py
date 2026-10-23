import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.triage.rules import is_emergency, extract_unit, extract_time, rule_triage
from src.triage.llm import triage


def test_gas_is_emergency():
    assert is_emergency("I can smell gas in the kitchen right now")


def test_squeaky_door_is_not_emergency():
    assert not is_emergency("door squeaks a bit, flat 12")


def test_extract_unit_time():
    assert extract_unit("tap leaking in room 204") == "204"
    assert extract_unit("A-203 mein pipe leak") == "A-203"
    assert extract_time("no power since morning") == "since morning"


def test_fallback_never_crashes_and_escalates():
    r = triage("sparks from the switchboard in flat 61")  # no API key in CI -> rules fallback
    assert r.urgency == "emergency" and r.needs_human_review

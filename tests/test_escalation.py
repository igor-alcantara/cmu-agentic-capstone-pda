"""Escalation rules against the labeled case set. Both error rates are asserted."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pda.escalation import Signals, classify_sensitive, evaluate

CASES = json.loads((Path(__file__).resolve().parent.parent / "eval" / "labeled" / "escalation_cases.json")
                   .read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_labeled_escalation_case(case):
    events = evaluate(Signals(**case["signals"]))
    escalated = bool(events)
    if case.get("accepted_false_positive"):
        # ground truth is "no", the loose classifier fires anyway, and that cost is accepted
        assert escalated, "the accepted false positive is documented as firing; if it stops, update the label set"
        return
    assert escalated == case["expected_escalate"], case["why"]
    if case["expected_escalate"]:
        reasons = {e.reason for e in events}
        assert case["expected_reason"] in reasons, f"expected {case['expected_reason']}, got {reasons}"


def test_both_error_rates_on_labeled_set():
    """Missed escalations are the expensive error and must be zero. Unnecessary
    escalations are bounded by the cases explicitly accepted as false positives."""
    missed = unnecessary = 0
    accepted = sum(1 for c in CASES if c.get("accepted_false_positive"))
    for case in CASES:
        got = bool(evaluate(Signals(**case["signals"])))
        if case["expected_escalate"] and not got:
            missed += 1
        if not case["expected_escalate"] and got:
            unnecessary += 1
    assert missed == 0
    assert unnecessary <= accepted


def test_classifier_is_loose_on_purpose():
    assert "compensation" in classify_sensitive("Can this plan help me get a raise next cycle?")
    assert "accommodation" in classify_sensitive("I need reduced hours for medical reasons.")
    assert classify_sensitive("I want to raise my Spark level before the next project.") == ["compensation"], \
        "a false positive like this is accepted: one review is cheaper than a missed compensation topic"
    assert classify_sensitive("Get certified on Qlik Cloud administration.") == []

"""Escalation to a human, evaluated after each phase (checkpoint 6.1).

Four tiers, each enforced here in code, none in a prompt:

- categorical: any external side effect goes to the employee for approval;
  anything entering a formal record routes to L&D.
- deterministic: missing or conflicting role document, stale snapshot, retry
  cap reached, cost or wall-clock threshold.
- classifier: one deliberately loose keyword net for performance, promotion,
  compensation, and accommodation topics. A false positive costs one review;
  a false negative is a policy violation, so the net is wide on purpose.
- judgment: a thin margin between the top two branches. Its only consequence
  is that the employee sees both options.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from pda.models import EscalationEvent

SENSITIVE_PATTERNS = {
    "performance": r"\b(performance (review|rating|improvement)|pip|underperform\w*|rated|my rating)\b",
    "promotion": r"\b(promot\w+|level up to|next level|senior title|get promoted)\b",
    "compensation": r"\b(compensat\w+|salary|salaries|pay (raise|band|grade)|raise|bonus|equity|stock)\b",
    "accommodation": r"\b(accommodat\w+|disabilit\w+|medical leave|reduced hours|adhd|dyslexi\w+)\b",
}


class Signals(BaseModel):
    """Everything the escalation rules look at. Filled by the Orchestrator."""

    model_config = ConfigDict(extra="forbid")

    phase: str
    employee_request: str = ""
    action_kinds: list[str] = []
    enters_formal_record: bool = False
    precondition_status: str = "ok"
    snapshot_age_days: int = 0
    stale_after_days: int = 45
    retry_count: int = 0
    retry_cap: int = 1
    gathering_failed: bool = False  # a gathering step is still failed after the retries
    cost_usd: float = 0.0
    cost_cap_usd: float = 2.0
    elapsed_seconds: float = 0.0
    wall_cap_seconds: float = 300.0
    close_call: bool = False


def classify_sensitive(text: str) -> list[str]:
    hits = []
    for topic, pattern in SENSITIVE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(topic)
    return hits


def evaluate(s: Signals) -> list[EscalationEvent]:
    events: list[EscalationEvent] = []
    ph = s.phase

    # categorical
    if s.action_kinds:
        events.append(EscalationEvent(tier="categorical", reason="external_side_effect", phase=ph,
                                      detail=f"drafted {', '.join(s.action_kinds)}; execution needs the employee's approval token"))
    if s.enters_formal_record:
        events.append(EscalationEvent(tier="categorical", reason="formal_record", phase=ph, route_to="ld",
                                      detail="output would enter a formal development record; L&D reviews"))

    # deterministic
    if s.precondition_status == "no_role_doc":
        events.append(EscalationEvent(tier="deterministic", reason="missing_role_doc", phase=ph,
                                      detail="no role document; plan labeled as ungrounded on role expectations"))
    elif s.precondition_status == "conflicting_docs":
        events.append(EscalationEvent(tier="deterministic", reason="conflicting_role_docs", phase=ph, route_to="ld",
                                      detail="more than one current role profile; L&D must say which applies"))
    if s.snapshot_age_days > s.stale_after_days:
        events.append(EscalationEvent(tier="deterministic", reason="stale_snapshot", phase=ph,
                                      detail=f"data snapshot is {s.snapshot_age_days} days old (limit {s.stale_after_days})"))
    if s.gathering_failed and s.retry_count >= s.retry_cap:
        events.append(EscalationEvent(tier="deterministic", reason="retry_cap", phase=ph,
                                      detail=f"gathering still failed after {s.retry_count} retry(ies), cap {s.retry_cap}; packet is partial"))
    if s.cost_usd > s.cost_cap_usd:
        events.append(EscalationEvent(tier="deterministic", reason="cost_threshold", phase=ph,
                                      detail=f"estimated cost {s.cost_usd:.2f} USD over cap {s.cost_cap_usd:.2f}"))
    if s.elapsed_seconds > s.wall_cap_seconds:
        events.append(EscalationEvent(tier="deterministic", reason="time_threshold", phase=ph,
                                      detail=f"{s.elapsed_seconds:.0f}s elapsed over cap {s.wall_cap_seconds:.0f}s"))

    # classifier (loose by design)
    topics = classify_sensitive(s.employee_request)
    if topics:
        events.append(EscalationEvent(tier="classifier", reason="sensitive_topic", phase=ph, route_to="ld",
                                      detail=f"request touches {', '.join(topics)}; a person answers that part"))

    # judgment
    if s.close_call:
        events.append(EscalationEvent(tier="judgment", reason="thin_margin", phase=ph,
                                      detail="top two plans are a close call; both shown to the employee"))
    return events

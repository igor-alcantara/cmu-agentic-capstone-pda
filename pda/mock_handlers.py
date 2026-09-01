"""Deterministic stand-ins for each model task, used by MockLLM.

Each handler sees exactly what the model would see (system and user prompt)
and computes a plausible answer from the structured content of the prompt.
They are not clever; they are predictable, so tests and the keyless demo
behave the same way every run.
"""
from __future__ import annotations

import json
import re

from pda.llm import MockLLM


def _field(user: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}: (.*)$", user, re.M)
    return m.group(1).strip() if m else ""


def profile_summary(system: str, user: str) -> str:
    name, role, gaps = _field(user, "Name"), _field(user, "Role"), _field(user, "Gaps")
    above, certs, limit = _field(user, "Above role level"), _field(user, "Certifications"), _field(user, "Weekly study limit")
    s = [f"{name} is a {role} with a study budget of {limit}."]
    s.append("There are no skill gaps against the role." if gaps == "none"
             else f"Against the role requirements the gaps are {gaps}.")
    if above != "none":
        s.append(f"{above} sits above the required level.")
    s.append("No certifications are on record." if certs == "none" else f"Certifications: {certs}.")
    return " ".join(s)


def orchestrator_policy(system: str, user: str) -> str:
    """What a well-behaved model does with the ReAct prompt: follow the phases,
    and when the last Observation reports a failure, use the one retry."""
    allowed = [a.strip() for a in _field(user, "Allowed actions").split(",") if a.strip()]
    observations = re.findall(r"^\s*Observation: (.*)$", user, re.M)
    last = observations[-1] if observations else ""
    if "FAILED" in last and "retry_gathering" in allowed:
        return json.dumps({"thought": "The last observation reports a failed gathering step. One retry is "
                                      "allowed before continuing with a partial packet.",
                           "action": "retry_gathering", "args": {}})
    order = ["run_profile_analysis", "run_context_research", "run_resource_scout", "freeze_packet",
             "synthesize_plan", "draft_actions", "finish"]
    reasons = {
        "run_profile_analysis": "Nothing has been gathered; start with the employee's own data.",
        "run_context_research": "The profile is in; retrieve what the role document expects.",
        "run_resource_scout": "The gap list exists, so the scout can search for resources.",
        "freeze_packet": "Every gathering step has reported; seal the packet before synthesis.",
        "synthesize_plan": "The packet is frozen; run the tree search over it.",
        "draft_actions": "A plan was chosen; draft the actions for the employee to approve.",
        "finish": "Nothing else is allowed; the run is complete.",
    }
    for a in order:
        if a in allowed:
            return json.dumps({"thought": reasons[a], "action": a, "args": {}})
    return json.dumps({"thought": "No allowed action remains.", "action": "finish", "args": {}})


def register_all(llm: MockLLM) -> None:
    llm.register("profile_summary", profile_summary)
    llm.register("orchestrator", orchestrator_policy)

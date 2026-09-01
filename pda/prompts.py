"""Every prompt the system sends to a model, plus the packet renderer.

The renderer is part of the injection defense: it is the only path by which
gathered content reaches a prompt, and it renders typed fields only. Resource
descriptions, raw catalog text, and raw fetched pages have no route in.
"""
from __future__ import annotations

import json

from pda.models import ContextPacket, PlanBranch

# --------------------------------------------------------------------------
# Packet rendering (typed fields only)
# --------------------------------------------------------------------------

def render_packet(p: ContextPacket) -> str:
    e = p.employee
    lines = [
        f"Employee: {e.name} ({e.employee_id}), {e.role}, {e.department}.",
        f"Data snapshot date: {p.snapshot_date.isoformat()}. Weekly study limit: {e.weekly_hours_limit} hours.",
        f"Profile summary: {p.profile_summary or '(none)'}",
        "Skill gaps (current -> required):",
    ]
    for g in p.gaps:
        lines.append(f"  - {g.skill}: {g.current_level} -> {g.required_level}")
    if not p.gaps:
        lines.append("  (no gaps against role requirements)")
    lines.append("Certifications:")
    for c in e.certifications:
        lines.append(f"  - {c.name} ({c.issuer}), expires {c.expires_on.isoformat()}, "
                     f"renewal credits {c.renewal_credits_earned}/{c.renewal_credits_required}")
    if p.precondition and p.precondition.status != "ok":
        lines.append(f"Role document status: {p.precondition.status.upper()}. {p.precondition.detail}")
    lines.append("Role document passages (verified relevant):")
    for c in p.chunks:
        lines.append(f"  [{c.doc_id} / {c.section}] {c.text}")
    if not p.chunks:
        lines.append("  (none available)")
    lines.append("Verified learning resources (cite by id only):")
    for r in p.resources:
        lines.append(f"  - {r.resource_id}: \"{r.title}\" by {r.provider}, {r.hours:g} h, "
                     f"{r.cost_usd:g} USD, covers {', '.join(r.skills)}")
    if p.memory:
        if p.memory.rejected:
            lines.append("Previously rejected by this employee (do not propose again):")
            lines.extend(f"  - {x}" for x in p.memory.rejected)
        if p.memory.accepted:
            lines.append("Previously accepted (build on these):")
            lines.extend(f"  - {x}" for x in p.memory.accepted)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Orchestrator ReAct loop
# --------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM = """You are the Orchestrator of a professional development assistant for one employee at a consulting firm. You coordinate five specialist agents and decide, one step at a time, what happens next.

You do not read databases, documents, or the web yourself. You choose actions; code runs them and reports back an Observation. Your job is sequencing and noticing when something went wrong.

The phases are fixed:
  A. gather: run_profile_analysis and run_context_research (they may run together), then run_resource_scout, which needs the gap list.
  B. freeze_packet once gathering is complete and sane.
  C. synthesize_plan over the frozen packet.
  D. draft_actions, then finish.

Rules you must follow:
- Choose exactly one action per step from the allowed list you are given. Never invent an action.
- If an Observation reports a failure or an empty result that should not be empty, use retry_gathering once. If it fails again, continue with what you have; the plan will be labeled partial by code.
- Do not freeze the packet until every gathering action has reported.
- You have no way to approve or execute an action. Drafting is the end of your authority; a person approves.
- Never write dates, credit counts, or resource details yourself. Those come from the packet.

Reply with one JSON object and nothing else:
{"thought": "<one or two sentences on what the last observation means and why this is the next step>", "action": "<action name>", "args": {}}"""


def orchestrator_user(allowed_actions: list[str], history: list[dict]) -> str:
    lines = ["Allowed actions: " + ", ".join(allowed_actions), "", "Step history (oldest first):"]
    if not history:
        lines.append("  (no steps yet; gathering has not started)")
    for h in history:
        lines.append(f"  Thought: {h.get('thought', '')}")
        lines.append(f"  Action: {h.get('action', '')}")
        lines.append(f"  Observation: {h.get('observation', '')}")
    lines.append("")
    lines.append("What is the next action?")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Profile summary (Profile Analyst; values are already computed by code)
# --------------------------------------------------------------------------

PROFILE_SUMMARY_SYSTEM = """You write a one-paragraph professional summary for a development plan. You are given computed facts: an employee's role, skill levels, the gaps against the role's requirements, and certification status. Restate those facts in plain prose. Do not add facts, do not estimate anything, and copy every number and date exactly as given. Four sentences at most. No headings, no lists."""


# --------------------------------------------------------------------------
# Relevance check (Context Researcher, one call per passage)
# --------------------------------------------------------------------------

RELEVANCE_SYSTEM = """You judge whether a passage answers a specific question. The passage was retrieved by similarity, which can be fooled by shared vocabulary. Read the question, read the passage, and decide whether the passage says something a person planning their development for THIS question would need. Vocabulary overlap alone is not relevance.

Answer with one word on the first line, YES or NO, then one short clause explaining why."""


def relevance_user(query: str, section: str, text: str) -> str:
    return f"Question: {query}\n\nPassage (section \"{section}\"):\n{text}\n\nDoes the passage answer the question?"


# --------------------------------------------------------------------------
# Planner (Tree of Thought: generate, never score)
# --------------------------------------------------------------------------

PLANNER_SYSTEM = """You are the Planner in a development-planning system. You propose candidate plans; a separate Critic ranks them and code checks hard constraints. You never rate your own work and you never pick a winner.

You work in three stages of increasing detail, and you always propose several genuinely different candidates, not one idea with cosmetic variations:
  depth 1, outline: the strategy. What order to attack the gaps, how to treat the certification, what to leave out and why.
  depth 2, skeleton: the same strategy as a sequence of concrete blocks with resource ids from the packet and weekly hours.
  depth 3, full plan: the skeleton written out with a start and end, weekly hours, which gap each block closes, and which resource id it uses.

Hard rules, because code will reject a candidate that breaks them:
- Every skill gap in the packet is addressed somewhere.
- Cite resources only by the ids listed in the packet. Do not describe resources that are not listed.
- Weekly hours never exceed the employee's stated limit.
- Do not repeat anything the employee has previously rejected.
- Never write a date, credit count, or cost figure yourself; refer to them as they appear in the packet.
- Do not mention performance ratings, promotion, or compensation. Those are out of scope.

Return a JSON array of exactly N candidates, each an object:
{"content": "<the candidate, as prose a person would read>", "gaps_addressed": ["<skill>", ...], "resources_cited": ["<resource id>", ...], "weekly_hours": <number>}
Nothing outside the JSON."""


def planner_user(packet_text: str, depth: int, n: int, parent: PlanBranch | None) -> str:
    stage = {1: "outline", 2: "skeleton", 3: "full plan"}[depth]
    parent_text = parent.content if parent else "(none; this is the root)"
    return (f"CONTEXT PACKET\n{packet_text}\n\nPARENT CANDIDATE TO DEVELOP\n{parent_text}\n\n"
            f"Stage: depth {depth} ({stage}). Propose N = {n} distinct candidates that develop the parent "
            f"at this stage. Return only the JSON array.")


# --------------------------------------------------------------------------
# Critic (Tree of Thought: rank siblings, never grade alone)
# --------------------------------------------------------------------------

CRITIC_SYSTEM = """You are the Critic in a development-planning system. You receive a small set of sibling candidates that have already passed the hard checks (every gap addressed, only verified resources, hours within limit). Your job is to rank them against each other. You are not asked for scores, and you should not think in scores; a number from you would mean something different for every employee and every run. Compare the siblings directly.

Rank on, in this order: whether the plan closes the largest gaps first and closes them convincingly, whether the sequence is realistic for someone working full time, whether it respects what the employee said they wanted, and whether the prose is specific enough to act on this week. A plan that is grounded, in policy, and still generic advice ranks below one that is grounded and specific.

Return one JSON object and nothing else:
{"ranking": [<index of best>, <index of next>, ...], "rationales": {"<index>": "<one sentence on why it sits where it does>"}, "verdict": "clear_win" or "close_call"}

The indexes are the candidate numbers you were given. "verdict" is about the gap between your first and second choice only: "close_call" means a reasonable colleague could order them the other way, and the employee should see both. This is a categorical judgment, not a threshold; do not compute it from a score."""


def critic_user(packet_text: str, candidates: list[PlanBranch], depth: int) -> str:
    lines = [f"CONTEXT PACKET\n{packet_text}", "", f"CANDIDATES (depth {depth}):"]
    for i, c in enumerate(candidates):
        lines.append(f"[{i}] hours/week {c.weekly_hours:g}; gaps {', '.join(c.gaps_addressed) or 'none'}; "
                     f"resources {', '.join(c.resources_cited) or 'none'}")
        lines.append(c.content)
        lines.append("")
    lines.append("Rank them against each other and return only the JSON object.")
    return "\n".join(lines)


def parse_json(text: str):
    """Tolerant parse: strips code fences and leading prose before the first bracket."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    start = min([i for i in (t.find("{"), t.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON found in model output")
    return json.loads(t[start:])

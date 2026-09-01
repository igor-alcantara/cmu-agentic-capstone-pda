"""Planner: the Tree-of-Thought thought generator. Proposes, never scores.

Candidates come back as typed ``PlanBranch`` objects. The Planner may say
how many weeks a plan takes; the schedule dates themselves are set here by
code from the run clock, never written by the model.
"""
from __future__ import annotations

from datetime import date, timedelta

from pda.llm import LLM
from pda.models import PlanBranch
from pda.prompts import PLANNER_SYSTEM, parse_json, planner_user


def propose(packet_text: str, depth: int, n: int, parent: PlanBranch | None, llm: LLM, today: date
            ) -> list[PlanBranch]:
    raw = llm.complete("planner", PLANNER_SYSTEM, planner_user(packet_text, depth, n, parent), max_tokens=4000)
    try:
        items = parse_json(raw)
        if not isinstance(items, list):
            items = []
    except ValueError:
        items = []
    branches: list[PlanBranch] = []
    pid = parent.branch_id if parent else "root"
    for i, it in enumerate(items[:n]):
        if not isinstance(it, dict):
            continue
        weeks = it.get("weeks")
        start = end = None
        if isinstance(weeks, (int, float)) and weeks > 0:
            start = today
            end = today + timedelta(weeks=int(weeks)) - timedelta(days=1)
        try:
            hours = float(it.get("weekly_hours", 0) or 0)
        except (TypeError, ValueError):
            hours = 0.0
        branches.append(PlanBranch(
            branch_id=f"d{depth}-{pid}-{i}", depth=depth, parent_id=parent.branch_id if parent else None,
            content=str(it.get("content", "")).strip(),
            gaps_addressed=[str(g) for g in it.get("gaps_addressed", []) or []],
            resources_cited=[str(r) for r in it.get("resources_cited", []) or []],
            weekly_hours=hours, schedule_start=start, schedule_end=end))
    return branches

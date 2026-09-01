"""Critic: rank sibling candidates relative to each other. Never an absolute grade.

The Critic only ever sees candidates that passed the deterministic hard
checks. It returns an ordering plus one categorical verdict about the gap
between first and second place. No number from the Critic gates anything;
the beam keeps the top k of its ordering, and that is the whole mechanism.
"""
from __future__ import annotations

from pda.llm import LLM
from pda.models import PlanBranch
from pda.prompts import CRITIC_SYSTEM, critic_user, parse_json


def degenerate(branch: PlanBranch) -> bool:
    """The only absolute floor: catches empty or near-empty output, nothing subtler."""
    return len(branch.content.split()) < 12


def rank(packet_text: str, candidates: list[PlanBranch], depth: int, llm: LLM
         ) -> tuple[list[PlanBranch], str, bool]:
    """Return (candidates in rank order, verdict, parsed_ok)."""
    if len(candidates) == 1:
        only = candidates[0].model_copy(update={"critic_rank": 1, "critic_rationale": "sole survivor of the hard checks"})
        return [only], "clear_win", True
    raw = llm.complete("critic", CRITIC_SYSTEM, critic_user(packet_text, candidates, depth), max_tokens=1500)
    order: list[int] = []
    rationales: dict[str, str] = {}
    verdict = "clear_win"
    parsed_ok = True
    try:
        data = parse_json(raw)
        seen = set()
        for x in data.get("ranking", []):
            i = int(x)
            if 0 <= i < len(candidates) and i not in seen:
                order.append(i)
                seen.add(i)
        rationales = {str(k): str(v) for k, v in (data.get("rationales") or {}).items()}
        if data.get("verdict") in ("clear_win", "close_call"):
            verdict = data["verdict"]
    except (ValueError, AttributeError, TypeError):
        parsed_ok = False
    if not order:
        parsed_ok = False
    # anything the Critic forgot keeps its original relative order at the back
    order += [i for i in range(len(candidates)) if i not in order]
    ranked = []
    for pos, i in enumerate(order, start=1):
        note = rationales.get(str(i), "") if parsed_ok else "critic output unparseable; input order kept"
        ranked.append(candidates[i].model_copy(update={"critic_rank": pos, "critic_rationale": note}))
    return ranked, verdict, parsed_ok

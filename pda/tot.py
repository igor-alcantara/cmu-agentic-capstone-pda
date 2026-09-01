"""Phase C: Tree-of-Thought beam search over the frozen packet (checkpoint 4.1).

Beam width 2, branching factor 3, depth 3: outline, then skeleton, then full
plan. At every depth the order of operations is fixed:

1. The Planner proposes candidates for each parent in the beam.
2. Deterministic hard checks reject candidates in code: every gap addressed,
   only verified resources cited, weekly hours within the employee's limit,
   schedule dates valid. The Critic never sees a rejected candidate.
3. A single absolute floor drops degenerate (near-empty) output.
4. The Critic ranks the survivors against each other; the beam keeps the top
   two. The Critic's verdict on the final depth ("clear win" or "close call")
   is the thin-margin trigger. It is categorical, not a score threshold.

Lesson 1 in code: the learned signal only orders a set that the rules have
already bounded.
"""
from __future__ import annotations

from datetime import date

from pda.agents import critic, planner
from pda.config import Settings
from pda.guardrails.budget import Budget
from pda.llm import LLM
from pda.models import ContextPacket, PlanBranch, PlanResult
from pda.prompts import render_packet
from pda.state import StateStore

MAX_WEEKS = 26


def hard_check(branch: PlanBranch, packet: ContextPacket, depth: int) -> list[str]:
    """Reasons the candidate fails. Empty list means it may go to the Critic."""
    reasons: list[str] = []
    missing = {g.skill for g in packet.gaps} - set(branch.gaps_addressed)
    if missing:
        reasons.append(f"gaps not addressed: {', '.join(sorted(missing))}")
    known = {r.resource_id for r in packet.resources}
    unknown = set(branch.resources_cited) - known
    if unknown:
        reasons.append(f"unverified resources cited: {', '.join(sorted(unknown))}")
    limit = packet.employee.weekly_hours_limit
    if branch.weekly_hours <= 0 or branch.weekly_hours > limit:
        reasons.append(f"weekly hours {branch.weekly_hours:g} outside (0, {limit}]")
    if depth >= 2 and packet.resources and not branch.resources_cited:
        reasons.append("no resources cited at a stage that requires them")
    if depth >= 3:
        if branch.schedule_start is None or branch.schedule_end is None:
            reasons.append("no schedule length given for the full plan")
        elif branch.schedule_end <= branch.schedule_start:
            reasons.append("schedule dates invalid")
        elif (branch.schedule_end - branch.schedule_start).days > MAX_WEEKS * 7:
            reasons.append(f"schedule longer than {MAX_WEEKS} weeks")
    return reasons


def make_synthesizer(settings: Settings):
    def synthesize(packet: ContextPacket, llm: LLM, budget: Budget, store: StateStore, today: date) -> PlanResult:
        packet_text = render_packet(packet)
        beam: list[PlanBranch | None] = [None]
        explored: list[PlanBranch] = []
        verdict = "clear_win"
        for depth in range(1, settings.depth + 1):
            survivors: list[PlanBranch] = []
            rejected = 0
            for parent in beam:
                for cand in planner.propose(packet_text, depth, settings.branching_factor, parent, llm, today):
                    reasons = hard_check(cand, packet, depth)
                    explored.append(cand.model_copy(update={"critic_rationale": "; ".join(reasons)}) if reasons else cand)
                    store.log("tot_candidate", {"branch": cand.branch_id, "depth": depth,
                                                "hard_check": "pass" if not reasons else "reject", "reasons": reasons})
                    if reasons:
                        rejected += 1
                    elif critic.degenerate(cand):
                        rejected += 1
                        store.log("tot_candidate", {"branch": cand.branch_id, "depth": depth, "hard_check": "degenerate"})
                    else:
                        survivors.append(cand)
            if not survivors:
                best = next((b for b in beam if b is not None), None)
                store.log("tot_depth", {"depth": depth, "survivors": 0, "rejected": rejected, "stopped": True})
                return PlanResult(status="partial", winner=best,
                                  partial_reason=f"no candidate passed the hard checks at depth {depth}",
                                  all_branches=explored)
            ranked, verdict, parsed_ok = critic.rank(packet_text, survivors, depth, llm)
            beam = ranked[:settings.beam_width]
            for r in ranked:  # carry rank and rationale into the explored record
                for i, e in enumerate(explored):
                    if e.branch_id == r.branch_id:
                        explored[i] = r
            store.log("tot_depth", {"depth": depth, "proposed": len(survivors) + rejected, "rejected": rejected,
                                    "ranking": [r.branch_id for r in ranked], "kept": [b.branch_id for b in beam],
                                    "verdict": verdict, "critic_parsed": parsed_ok})
        winner = beam[0]
        runner = beam[1] if len(beam) > 1 else None
        return PlanResult(status="complete", winner=winner, runner_up=runner,
                          close_call=(verdict == "close_call" and runner is not None), all_branches=explored)

    return synthesize

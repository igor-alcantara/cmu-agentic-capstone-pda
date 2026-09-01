"""Command line entry point.

    python -m pda.cli --employee E007 --mock
    python -m pda.cli --employee E007                # real mode, needs ANTHROPIC_API_KEY in .env
    python -m pda.cli --employee E007 --mock --auto-approve-none   # headless, drafts only
    python -m pda.cli --employee E001 --mock --today 2026-12-01    # simulate a stale snapshot

Prints the ReAct trace, escalations, the chosen plan (both plans on a close
call), and each draft. Then, per draft, asks for approval. A "yes" creates a
HumanConfirmation, which issues the token that lets ``drafting.execute`` write
the artifact to outbox/. Anything else leaves the draft as a draft.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from pda.config import load_settings
from pda.drafting import draft, execute
from pda.guardrails.approvals import ApprovalRegistry, HumanConfirmation
from pda.models import LongTermMemory, PlanBranch
from pda.orchestrator import Orchestrator, RunResult
from pda.tot import make_synthesizer

RULE = "-" * 78


def _print_branch(label: str, b: PlanBranch) -> None:
    print(f"{label} [{b.branch_id}] {b.weekly_hours:g} h/week"
          + (f", {b.schedule_start} to {b.schedule_end}" if b.schedule_start else ""))
    print(f"  gaps: {', '.join(b.gaps_addressed)}; resources: {', '.join(b.resources_cited) or 'none'}")
    if b.critic_rationale:
        print(f"  critic: {b.critic_rationale}")
    print()
    for line in b.content.splitlines():
        print(f"  {line}")
    print()


def print_run(result: RunResult) -> None:
    print(RULE)
    print(f"Professional Development Assistant | employee {result.employee_id} | status {result.status}")
    print(RULE)
    print("ReAct trace")
    for i, h in enumerate(result.history, start=1):
        print(f"  {i}. Thought: {h['thought']}")
        print(f"     Action: {h['action']}")
        print(f"     Observation: {h['observation']}")
    print()
    print(f"Context packet frozen with hash {result.packet_hash}; "
          f"{len(result.packet.chunks)} passages, {len(result.packet.resources)} verified resources, "
          f"{result.packet.unverified_dropped} unverified claims dropped")
    if result.packet.precondition and result.packet.precondition.status != "ok":
        print(f"  role document status: {result.packet.precondition.status}: {result.packet.precondition.detail}")
    print()
    print("Escalations" + (" (none)" if not result.escalations else ""))
    for e in result.escalations:
        print(f"  [{e.tier}] {e.reason} -> {e.route_to}: {e.detail}")
    print()
    plan = result.plan
    if plan is None:
        print("No plan was synthesized.")
        return
    print(f"Plan: {plan.status}" + (f" ({plan.partial_reason})" if plan.partial_reason else ""))
    print(f"  {len(plan.all_branches)} candidates explored, "
          f"{sum(1 for b in plan.all_branches if b.critic_rank is None and b.critic_rationale)} rejected by hard checks")
    print()
    if plan.winner:
        _print_branch("Chosen plan", plan.winner)
    if plan.close_call and plan.runner_up:
        print("The Critic called this a close call, so here is the runner-up as well.")
        _print_branch("Runner-up", plan.runner_up)
    print(f"Budget: {result.budget}")
    print()


def confirm_gate(result: RunResult, settings, auto_none: bool) -> None:
    if not result.drafts:
        print("No actions drafted.")
        return
    registry = ApprovalRegistry()
    memory = _load_memory(settings, result.employee_id)
    print(RULE)
    print(f"{len(result.drafts)} drafted action(s). Nothing executes without your approval.")
    print(RULE)
    for d in result.drafts:
        print(f"\n[{d.action_id}] {d.kind}: {d.title}")
        print("  " + "\n  ".join(d.body.splitlines()))
        if auto_none:
            print(f"  -> left as draft (--auto-approve-none)")
            continue
        answer = input(f"  Approve {d.action_id}? [y/N] ")
        conf = HumanConfirmation.from_prompt(d.action_id, answer)
        if conf is None:
            d.status = "rejected"
            if d.title not in memory.rejected:
                memory.rejected.append(d.title)
            print(f"  -> rejected; remembered so it is not proposed the same way again")
            continue
        token = registry.issue(conf)
        path = execute(d, token, registry, settings.outbox_dir, result.employee_id)
        d.status = "executed"
        if d.title not in memory.accepted:
            memory.accepted.append(d.title)
        print(f"  -> approved and executed: {path}")
    if not auto_none:
        _save_memory(settings, memory)
        print(f"\nLong-term memory updated: {settings.memory_dir / (result.employee_id + '.json')}")


def _load_memory(settings, employee_id: str) -> LongTermMemory:
    path = settings.memory_dir / f"{employee_id}.json"
    if path.exists():
        return LongTermMemory(**json.loads(path.read_text(encoding="utf-8")))
    return LongTermMemory(employee_id=employee_id)


def _save_memory(settings, memory: LongTermMemory) -> None:
    settings.memory_dir.mkdir(parents=True, exist_ok=True)
    (settings.memory_dir / f"{memory.employee_id}.json").write_text(
        json.dumps(memory.model_dump(), indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pda", description="Professional Development Assistant")
    ap.add_argument("--employee", required=True, help="employee id, e.g. E007")
    ap.add_argument("--mock", action="store_true", help="run against the deterministic MockLLM (no key)")
    ap.add_argument("--auto-approve-none", action="store_true", help="headless: leave every action as a draft")
    ap.add_argument("--today", type=date.fromisoformat, default=None, help="run clock (default: snapshot date)")
    ap.add_argument("--max-steps", type=int, default=20)
    args = ap.parse_args(argv)

    settings = load_settings(mock=True if args.mock else None)
    if not settings.mock and not settings.api_key:
        print("No ANTHROPIC_API_KEY found; running in mock mode. Use --mock to silence this.", file=sys.stderr)
        settings.mock = True
    orch = Orchestrator(settings, args.employee, synthesizer=make_synthesizer(settings), drafter=draft,
                        today=args.today)
    result = orch.run(max_steps=args.max_steps)
    print_run(result)
    confirm_gate(result, settings, args.auto_approve_none)
    print(f"\nRun log: {result.run_log}")
    return 0 if result.status == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())

"""Orchestrator: the ReAct loop, phase sequencing, memory, and the state store.

The model proposes one action per step; code decides which actions are
allowed at all (phase ordering is enforced here, not by the prompt), runs
the chosen one, and returns a typed Observation. Every step is logged to a
JSONL run log, which is the short-term memory of the run. Long-term memory
is one small JSON per employee, loaded at start and placed in the packet so
a rejected suggestion is not proposed again.

Synthesis and drafting are plugged in as callables. Until they are, the loop
finishes at the frozen packet. That keeps the seam explicit: Phase C and D
never run unless something is wired to run them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from pda.agents import context_researcher, profile_analyst
from pda.agents.resource_scout import scout
from pda.config import Settings
from pda.escalation import Signals, evaluate
from pda.guardrails.budget import Budget, BudgetExceeded, partial_plan
from pda.guardrails.scoped_db import ScopedConnection
from pda.guardrails.verifier import Catalog
from pda.llm import LLM, MockLLM, build_llm
from pda.mock_handlers import register_all
from pda.models import (ContextPacket, DraftAction, EscalationEvent, LongTermMemory, PlanResult)
from pda.prompts import ORCHESTRATOR_SYSTEM, orchestrator_user, parse_json
from pda.retrieval.index import RoleDocIndex
from pda.state import StateStore

GATHER = ("run_profile_analysis", "run_context_research", "run_resource_scout")
Synthesizer = Callable[[ContextPacket, LLM, Budget, StateStore], PlanResult]
Drafter = Callable[[ContextPacket, PlanResult, date], list[DraftAction]]


@dataclass
class RunResult:
    employee_id: str
    packet: ContextPacket
    packet_hash: str | None
    plan: PlanResult | None
    drafts: list[DraftAction]
    escalations: list[EscalationEvent]
    steps: list[dict[str, Any]]
    budget: dict[str, Any]
    status: str  # complete | partial
    run_log: Path | None = None
    history: list[dict[str, str]] = field(default_factory=list)


class Orchestrator:
    def __init__(self, settings: Settings, employee_id: str, *, llm: LLM | None = None,
                 budget: Budget | None = None, synthesizer: Synthesizer | None = None,
                 drafter: Drafter | None = None, today: date | None = None,
                 run_log_path: Path | None = None) -> None:
        self.settings = settings
        self.employee_id = employee_id
        self.budget = budget or Budget(settings.max_tool_calls, settings.max_total_tokens, settings.max_wall_seconds)
        self.llm = llm or build_llm(settings, self.budget)
        if isinstance(self.llm, MockLLM):
            register_all(self.llm)
        self.synthesizer = synthesizer
        self.drafter = drafter
        self.db = ScopedConnection(settings.db_path, employee_id)
        self.index = RoleDocIndex(settings.role_docs_dir)
        self.catalog = Catalog(settings.catalog_path)
        self.taxonomy = profile_analyst.taxonomy(self.db)
        snapshot = profile_analyst.snapshot_date(self.db)
        # The run clock is pinned to the snapshot date unless told otherwise, so the
        # synthetic scenario is stable. Pass today= to simulate a stale snapshot.
        self.today = today or snapshot
        profile = profile_analyst.load_profile(self.db)
        memory = self._load_memory()
        self.store = StateStore(ContextPacket(employee=profile, snapshot_date=snapshot, memory=memory),
                                run_log_path or settings.runs_dir / f"{employee_id}.jsonl")
        self.history: list[dict[str, str]] = []
        self.done: set[str] = set()
        self.failed: set[str] = set()
        self.retries = 0
        self.plan: PlanResult | None = None
        self.drafts: list[DraftAction] | None = None
        self.escalations: list[EscalationEvent] = []
        # In mock mode the first scout call fails on purpose, so the loop's recovery is demonstrable.
        self._scripted_failure = isinstance(self.llm, MockLLM)

    # ----- memory --------------------------------------------------------
    def _load_memory(self) -> LongTermMemory:
        path = self.settings.memory_dir / f"{self.employee_id}.json"
        if path.exists():
            return LongTermMemory(**json.loads(path.read_text(encoding="utf-8")))
        return LongTermMemory(employee_id=self.employee_id)

    # ----- phase gating (code, not prompt) ---------------------------------
    def allowed_actions(self) -> list[str]:
        if not self.store.frozen:
            allowed = [a for a in GATHER if a not in self.done]
            if self.failed and self.retries < self.settings.max_gathering_retries:
                allowed.append("retry_gathering")
            if all(a in self.done for a in GATHER):
                allowed.append("freeze_packet")
            return allowed
        if self.synthesizer and self.plan is None:
            return ["synthesize_plan"]
        if self.drafter and self.plan is not None and self.drafts is None:
            return ["draft_actions"]
        return ["finish"]

    # ----- one ReAct step --------------------------------------------------
    def step(self) -> str:
        allowed = self.allowed_actions()
        raw = self.llm.complete("orchestrator", ORCHESTRATOR_SYSTEM, orchestrator_user(allowed, self.history),
                                max_tokens=300)
        try:
            decision = parse_json(raw)
            thought, action = str(decision.get("thought", "")), str(decision.get("action", ""))
        except (ValueError, AttributeError):
            thought, action = "(unparseable model output)", ""
        if action not in allowed:
            observation = f"REJECTED: '{action}' is not allowed now. Allowed: {', '.join(allowed)}"
            action = action or "(none)"
        else:
            self.budget.charge_tool(action)
            observation = self._dispatch(action)
        self.history.append({"thought": thought, "action": action, "observation": observation})
        self.store.log("react_step", {"thought": thought, "action": action, "observation": observation,
                                      "allowed": allowed})
        return action

    def _dispatch(self, action: str) -> str:
        if action == "run_profile_analysis":
            profile, gaps, above, summary = profile_analyst.analyze(self.db, self.llm, self.today)
            self.store.update(employee=profile, gaps=gaps, profile_summary=summary)
            self.done.add(action)
            return (f"profile loaded for {profile.employee_id}; {len(gaps)} gap(s): "
                    f"{', '.join(g.skill for g in gaps) or 'none'}; above level: {', '.join(above) or 'none'}; "
                    f"{len(profile.certifications)} certification(s)")
        if action == "run_context_research":
            p = self.store.view()
            s = self.settings
            pre, chunks, queries = context_researcher.research(
                self.index, p.employee.role, p.gaps, self.llm, top_k=s.retrieval_top_k,
                keep_min=s.retrieval_keep_min, keep_max=s.retrieval_keep_max, floor=s.similarity_floor)
            self.store.update(precondition=pre, chunks=chunks)
            self.done.add(action)
            if pre.status != "ok":
                return f"role document precondition {pre.status.upper()}: {pre.detail}; 0 passages (labeled fallback)"
            return f"{len(chunks)} relevant passage(s) from {len({c.doc_id for c in chunks})} document(s) over {len(queries)} queries"
        if action == "run_resource_scout":
            p = self.store.view()
            if "run_profile_analysis" not in self.done:
                return "REJECTED: the gap list does not exist yet; run profile analysis first"
            if self._scripted_failure:
                self._scripted_failure = False
                self.failed.add(action)
                return "FAILED: resource scout returned 0 resources (simulated transient catalog outage)"
            resources, dropped, queries = scout(p.gaps, self.taxonomy, self.catalog)
            self.store.update(resources=resources, unverified_dropped=dropped)
            self.done.add(action)
            self.failed.discard(action)
            return (f"{len(resources)} verified resource(s) over {len(queries)} allowlisted queries; "
                    f"{dropped} unverified claim(s) dropped")
        if action == "retry_gathering":
            self.retries += 1
            failed = sorted(self.failed)
            results = [f"{a} -> {self._dispatch(a)}" for a in failed]
            return f"retry {self.retries}/{self.settings.max_gathering_retries}: " + "; ".join(results)
        if action == "freeze_packet":
            self._escalate("gather")
            h = self.store.freeze()
            p = self.store.view()
            return (f"packet frozen (hash {h}); {len(p.gaps)} gaps, {len(p.chunks)} passages, "
                    f"{len(p.resources)} resources, {len(self.escalations)} escalation(s) so far")
        if action == "synthesize_plan":
            assert self.synthesizer is not None
            self.plan = self.synthesizer(self.store.view(), self.llm, self.budget, self.store)
            self._escalate("synthesize")
            w = self.plan.winner
            return (f"plan {self.plan.status}; winner {w.branch_id if w else 'none'}; "
                    f"close call: {self.plan.close_call}; {len(self.plan.all_branches)} branches explored")
        if action == "draft_actions":
            assert self.drafter is not None and self.plan is not None
            self.drafts = self.drafter(self.store.view(), self.plan, self.today)
            self._escalate("act")
            return f"{len(self.drafts)} action(s) drafted: {', '.join(d.kind for d in self.drafts)}; awaiting human approval"
        if action == "finish":
            return "run complete"
        return f"REJECTED: unknown action {action!r}"

    # ----- escalation after each phase ------------------------------------
    def _escalate(self, phase: str) -> None:
        p = self.store.view()
        signals = Signals(
            phase=phase, employee_request=p.employee.request,
            action_kinds=[d.kind for d in (self.drafts or [])] if phase == "act" else [],
            precondition_status=p.precondition.status if (p.precondition and phase == "gather") else "ok",
            snapshot_age_days=(self.today - p.snapshot_date).days if phase == "gather" else 0,
            stale_after_days=self.settings.stale_snapshot_days,
            retry_count=self.retries if phase == "gather" else 0, retry_cap=self.settings.max_gathering_retries,
            gathering_failed=bool(self.failed) if phase == "gather" else False,
            elapsed_seconds=self.budget.elapsed, wall_cap_seconds=self.settings.max_wall_seconds,
            close_call=bool(self.plan and self.plan.close_call) if phase == "synthesize" else False)
        if phase != "gather":
            signals.employee_request = ""  # the classifier runs once, on gather
        events = evaluate(signals)
        self.escalations.extend(events)
        for e in events:
            self.store.log("escalation", e.model_dump())
        if phase == "gather":
            self.store.update(escalations=list(self.escalations))

    # ----- the loop ----------------------------------------------------------
    def run(self, max_steps: int = 20) -> RunResult:
        status = "complete"
        try:
            for _ in range(max_steps):
                if self.step() == "finish":
                    break
            else:
                status = "partial"
                self.store.log("stopped", {"reason": f"max_steps {max_steps} reached"})
        except BudgetExceeded as exc:
            status = "partial"
            branches = self.plan.all_branches if self.plan else []
            self.plan = partial_plan(exc, branches)
            self.store.log("stopped", {"reason": str(exc)})
        if self.plan and self.plan.status == "partial":
            status = "partial"
        return RunResult(employee_id=self.employee_id, packet=self.store.view(), packet_hash=self.store.packet_hash,
                         plan=self.plan, drafts=self.drafts or [], escalations=list(self.escalations),
                         steps=list(self.store.steps), budget=self.budget.snapshot(), status=status,
                         run_log=self.store._log_path, history=list(self.history))

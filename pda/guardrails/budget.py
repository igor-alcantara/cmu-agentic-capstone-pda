"""Caps on tool calls, tokens, and wall clock.

Failure removed: a loop that runs until the bill or the clock stops it, and a
cap that fails silently. Hitting any cap raises ``BudgetExceeded``; the
Orchestrator turns that into a labeled partial plan through ``partial_plan``
rather than an empty result or a stack trace.
"""
from __future__ import annotations

import time
from typing import Callable

from pda.models import PlanBranch, PlanResult


class BudgetExceeded(RuntimeError):
    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind} cap exceeded: {detail}")
        self.kind = kind
        self.detail = detail


class Budget:
    def __init__(self, max_tool_calls: int, max_total_tokens: int, max_wall_seconds: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.max_tool_calls = max_tool_calls
        self.max_total_tokens = max_total_tokens
        self.max_wall_seconds = max_wall_seconds
        self._clock = clock
        self.started = clock()
        self.tool_calls = 0
        self.tokens = 0

    @property
    def elapsed(self) -> float:
        return self._clock() - self.started

    def check(self) -> None:
        if self.tool_calls > self.max_tool_calls:
            raise BudgetExceeded("tool_calls", f"{self.tool_calls} > {self.max_tool_calls}")
        if self.tokens > self.max_total_tokens:
            raise BudgetExceeded("tokens", f"{self.tokens} > {self.max_total_tokens}")
        if self.elapsed > self.max_wall_seconds:
            raise BudgetExceeded("wall_clock", f"{self.elapsed:.1f}s > {self.max_wall_seconds}s")

    def charge_tool(self, name: str = "") -> None:
        self.tool_calls += 1
        self.check()

    def charge_tokens(self, n: int) -> None:
        self.tokens += max(0, n)
        self.check()

    def snapshot(self) -> dict:
        return {"tool_calls": self.tool_calls, "tokens": self.tokens,
                "elapsed_seconds": round(self.elapsed, 2)}


def partial_plan(exc: BudgetExceeded, branches: list[PlanBranch]) -> PlanResult:
    """The labeled partial. Best surviving branch so far, clearly marked."""
    best = branches[-1] if branches else None
    return PlanResult(status="partial",
                      partial_reason=f"stopped by {exc.kind} cap ({exc.detail})",
                      winner=best, all_branches=list(branches))

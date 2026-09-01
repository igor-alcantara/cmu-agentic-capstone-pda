"""Thin LLM boundary: one real client, one deterministic mock, one budget.

Every model call in the system goes through ``LLM.complete``. That is where the
token budget is charged, so a runaway loop hits the cap here rather than in
some agent that forgot to count.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Protocol

from pda.guardrails.budget import Budget

MockHandler = Callable[[str, str], str]


class LLM(Protocol):
    def complete(self, task: str, system: str, user: str, max_tokens: int = 2000) -> str: ...


class AnthropicLLM:
    """Calls the Anthropic Messages API. Thinking is left at the model default."""

    def __init__(self, api_key: str, model: str, budget: Budget) -> None:
        import anthropic  # lazy so mock mode never needs the package configured

        self._client = anthropic.Anthropic(api_key=api_key or None)
        self._model = model
        self._budget = budget

    def complete(self, task: str, system: str, user: str, max_tokens: int = 2000) -> str:
        self._budget.check()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        usage = response.usage
        self._budget.charge_tokens(usage.input_tokens + usage.output_tokens)
        if response.stop_reason == "refusal":
            return ""
        return "".join(b.text for b in response.content if b.type == "text").strip()


class MockLLM:
    """Deterministic stand-in keyed on a hash of the prompt.

    Agents register a handler per ``task`` name. A handler receives the system
    and user prompt text and returns what a model plausibly would, computed
    from the structured content of the prompt. Unregistered tasks get a stable
    placeholder string so nothing depends on a network call.
    """

    def __init__(self, budget: Budget) -> None:
        self._budget = budget
        self._handlers: dict[str, MockHandler] = {}
        self.calls: list[tuple[str, str, str]] = []  # (task, system, user)

    def register(self, task: str, handler: MockHandler) -> None:
        self._handlers[task] = handler

    def complete(self, task: str, system: str, user: str, max_tokens: int = 2000) -> str:
        self._budget.check()
        self.calls.append((task, system, user))
        self._budget.charge_tokens((len(system) + len(user)) // 4 + 50)
        handler = self._handlers.get(task)
        if handler is not None:
            return handler(system, user)
        digest = hashlib.sha256(f"{task}|{system}|{user}".encode()).hexdigest()[:8]
        return f"[mock:{task}:{digest}]"


def build_llm(settings, budget: Budget) -> LLM:
    if settings.mock or not settings.api_key:
        return MockLLM(budget)
    return AnthropicLLM(settings.api_key, settings.model, budget)

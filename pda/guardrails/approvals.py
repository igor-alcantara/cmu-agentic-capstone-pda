"""Two-phase actions: the model drafts, a human-issued token executes.

Failure removed: an action executing because the model said it was approved.
Tokens are 128-bit random values that exist only in this registry's memory,
issued only when a ``HumanConfirmation`` is presented, and checked with a
constant-time compare by ``check``. Model output is text; text cannot produce
a ``HumanConfirmation`` and cannot guess a token. The executing function is
not exposed to the model as a tool at all.
"""
from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class HumanConfirmation:
    """Constructed only by the CLI prompt after a person types yes."""

    action_id: str
    answered: str

    @classmethod
    def from_prompt(cls, action_id: str, answer: str) -> "HumanConfirmation | None":
        if answer.strip().lower() in {"y", "yes"}:
            return cls(action_id=action_id, answered=answer.strip())
        return None


class ApprovalRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}
        self.issued: list[str] = []
        self.rejected_checks: int = 0

    def issue(self, confirmation: HumanConfirmation) -> str:
        if not isinstance(confirmation, HumanConfirmation):
            raise PermissionError("approval requires a HumanConfirmation from the CLI")
        token = secrets.token_hex(16)
        self._tokens[confirmation.action_id] = token
        self.issued.append(confirmation.action_id)
        return token

    def check(self, action_id: str, token: str) -> bool:
        """Single use: a valid token is consumed on success."""
        expected = self._tokens.get(action_id)
        if expected is None or not isinstance(token, str):
            self.rejected_checks += 1
            return False
        if not hmac.compare_digest(expected, token):
            self.rejected_checks += 1
            return False
        del self._tokens[action_id]
        return True

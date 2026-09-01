"""Shared state store and run log.

The Orchestrator is the only writer. ``freeze()`` seals the context packet
before synthesis and records its hash, so the Planner and Critic reason over
one immutable snapshot rather than a moving target. Agents get copies, never
references.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pda.models import ContextPacket


class FrozenPacketError(RuntimeError):
    """Raised when anything tries to mutate the packet after freeze()."""


class StateStore:
    def __init__(self, packet: ContextPacket, run_log_path: Path | None = None) -> None:
        self._packet = packet
        self._frozen = False
        self.packet_hash: str | None = None
        self._log_path = run_log_path
        self.steps: list[dict[str, Any]] = []
        if run_log_path is not None:
            run_log_path.parent.mkdir(parents=True, exist_ok=True)
            run_log_path.write_text("", encoding="utf-8")

    # ----- packet access -----------------------------------------------
    @property
    def frozen(self) -> bool:
        return self._frozen

    def update(self, **fields: Any) -> None:
        if self._frozen:
            raise FrozenPacketError("context packet is frozen; no writes allowed after Phase B")
        self._packet = self._packet.model_copy(update=fields)

    def view(self) -> ContextPacket:
        """Read-only copy. Mutating it changes nothing in the store."""
        return self._packet.model_copy(deep=True)

    def freeze(self) -> str:
        payload = self._packet.model_dump_json(exclude={"escalations"})
        self.packet_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        self._frozen = True
        self.log("freeze_packet", {"hash": self.packet_hash, "chunks": len(self._packet.chunks),
                                   "resources": len(self._packet.resources)})
        return self.packet_hash

    # ----- run log (short-term memory) -----------------------------------
    def log(self, kind: str, data: dict[str, Any]) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind, **data}
        self.steps.append(entry)
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")

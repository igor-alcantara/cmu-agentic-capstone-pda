"""Typed payloads shared by every agent.

Every object that crosses an agent boundary is one of these models. The
schemas are closed (``extra="forbid"``), which is itself a guardrail: there is
no field anywhere for a performance rating or a compensation figure, so no
agent can carry one even if a prompt tried to smuggle it in.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Certification(_Strict):
    name: str
    issuer: str
    issued_on: date
    expires_on: date
    renewal_credits_required: int = Field(ge=0)
    renewal_credits_earned: int = Field(ge=0)

    def days_to_expiry(self, today: date) -> int:
        return (self.expires_on - today).days


class EmployeeProfile(_Strict):
    employee_id: str
    name: str
    role: str
    department: str
    weekly_hours_limit: int = Field(ge=1, le=20)
    skills: dict[str, int]  # skill name -> level 1..5
    certifications: list[Certification]
    request: str = ""  # the employee's free-text ask for this run


class Gap(_Strict):
    skill: str
    current_level: int
    required_level: int

    @property
    def delta(self) -> int:
        return self.required_level - self.current_level


class RoleDocChunk(_Strict):
    doc_id: str
    role: str
    department: str
    updated: date
    section: str
    text: str
    similarity: float = 0.0
    relevant: bool | None = None


class Resource(_Strict):
    """A learning resource as the Orchestrator is allowed to see it.

    There is deliberately no ``description`` field. The Resource Scout reads
    catalog descriptions (untrusted text); what it hands over is this typed
    record, so an injection string in a description has no field to ride in.
    """

    resource_id: str
    title: str
    url: str
    provider: str
    skills: list[str]
    hours: float = Field(ge=0)
    cost_usd: float = Field(ge=0)
    verified: bool = False


class PlanBranch(_Strict):
    branch_id: str
    depth: int
    parent_id: str | None
    content: str
    gaps_addressed: list[str] = []
    resources_cited: list[str] = []  # resource_ids
    weekly_hours: float = 0.0
    schedule_start: date | None = None
    schedule_end: date | None = None
    critic_rank: int | None = None
    critic_rationale: str = ""


class DraftAction(_Strict):
    action_id: str
    kind: Literal["renewal_reminder", "calendar_block", "note"]
    title: str
    body: str
    slots: dict[str, str] = {}
    status: Literal["draft", "approved", "rejected", "executed"] = "draft"


class EscalationEvent(_Strict):
    tier: Literal["categorical", "deterministic", "classifier", "judgment"]
    reason: str
    detail: str
    phase: str
    route_to: Literal["employee", "ld"] = "employee"


class LongTermMemory(_Strict):
    employee_id: str
    accepted: list[str] = []
    rejected: list[str] = []


class PreconditionResult(_Strict):
    status: Literal["ok", "no_role_doc", "conflicting_docs"]
    doc_ids: list[str] = []
    detail: str = ""


class ContextPacket(_Strict):
    """Everything synthesis is allowed to reason over, frozen before Phase C."""

    employee: EmployeeProfile
    snapshot_date: date
    gaps: list[Gap] = []
    profile_summary: str = ""
    precondition: PreconditionResult | None = None
    chunks: list[RoleDocChunk] = []
    resources: list[Resource] = []
    unverified_dropped: int = 0
    memory: LongTermMemory | None = None
    escalations: list[EscalationEvent] = []


class PlanResult(_Strict):
    status: Literal["complete", "partial"]
    partial_reason: str = ""
    winner: PlanBranch | None = None
    runner_up: PlanBranch | None = None
    close_call: bool = False
    all_branches: list[PlanBranch] = []

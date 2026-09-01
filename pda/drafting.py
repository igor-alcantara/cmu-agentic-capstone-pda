"""Phase D: draft actions from the winning plan, then execute only with a token.

Drafts are templates. Every exact value (a date, a credit count, an hour
figure) is filled by ``guardrails.slots`` from typed objects; the prose is
fixed. The model chose the plan; it does not write the reminder.

``execute`` is the only function that produces an external effect (a file
in ``outbox/``, standing in for an email, a calendar entry, or a saved note).
It runs only when ``ApprovalRegistry.check`` accepts a token issued from a
``HumanConfirmation``. It is never registered as a tool the model can call.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from pda.guardrails.approvals import ApprovalRegistry
from pda.guardrails.slots import calendar_slots, fill, renewal_slots
from pda.models import ContextPacket, DraftAction, PlanResult

RENEWAL_WINDOW_DAYS = 90

RENEWAL_TEMPLATE = (
    "To: {{employee_name}}\n"
    "Subject: {{cert_name}} renewal due {{expires_on}}\n\n"
    "Hi {{employee_name}},\n\n"
    "Your {{cert_name}} certification from {{issuer}} expires on {{expires_on}}, which is {{days_to_expiry}} days "
    "from the current data snapshot. You have logged {{credits_earned}} of the {{credits_required}} renewal "
    "credits, so {{credits_remaining}} remain. The development plan puts the renewal work first so the credits "
    "are complete before the expiry date.\n\n"
    "This reminder was drafted by the Professional Development Assistant and sent only after you approved it."
)

CALENDAR_TEMPLATE = (
    "Calendar: recurring study block\n"
    "Title: Development plan study time\n"
    "Pattern: {{weekly_hours}} hours per week on weekday evenings, from {{start_date}} to {{end_date}} "
    "({{weeks}} weeks, {{total_hours}} hours in total).\n"
    "Notes: split as two sessions per week. Weekend blocks are not proposed."
)

NOTE_TEMPLATE = (
    "Personal development note (draft, not filed to any formal record)\n"
    "Employee: {{employee_name}}\n"
    "Snapshot: {{snapshot_date}}\n\n"
    "Chosen plan:\n{{plan_text}}\n\n"
    "Gaps addressed: {{gaps}}\n"
    "Resources: {{resources}}\n"
    "Weekly hours: {{weekly_hours}}"
)


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def draft(packet: ContextPacket, plan: PlanResult, today: date) -> list[DraftAction]:
    drafts: list[DraftAction] = []
    emp = packet.employee
    w = plan.winner
    if w is None:
        return drafts
    for i, cert in enumerate(emp.certifications):
        if 0 <= cert.days_to_expiry(today) <= RENEWAL_WINDOW_DAYS:
            slots = renewal_slots(emp, cert, today)
            drafts.append(DraftAction(action_id=f"A{len(drafts) + 1}", kind="renewal_reminder",
                                      title=f"Renewal reminder: {cert.name}", body=fill(RENEWAL_TEMPLATE, slots),
                                      slots=slots))
    if w.schedule_start and w.schedule_end and w.weekly_hours > 0:
        weeks = max(1, round((w.schedule_end - w.schedule_start).days / 7))
        slots = calendar_slots(_next_monday(today), w.weekly_hours, weeks)
        drafts.append(DraftAction(action_id=f"A{len(drafts) + 1}", kind="calendar_block",
                                  title="Study time calendar blocks", body=fill(CALENDAR_TEMPLATE, slots), slots=slots))
    titles = {r.resource_id: r.title for r in packet.resources}
    slots = {"employee_name": emp.name, "snapshot_date": packet.snapshot_date.isoformat(), "plan_text": w.content,
             "gaps": ", ".join(w.gaps_addressed) or "none",
             "resources": ", ".join(f"{rid} ({titles.get(rid, '?')})" for rid in w.resources_cited) or "none",
             "weekly_hours": f"{w.weekly_hours:g}"}
    drafts.append(DraftAction(action_id=f"A{len(drafts) + 1}", kind="note", title="Development plan note",
                              body=fill(NOTE_TEMPLATE, slots), slots={k: v for k, v in slots.items() if k != "plan_text"}))
    return drafts[:3]


def execute(action: DraftAction, token: str, registry: ApprovalRegistry, outbox: Path, employee_id: str) -> Path:
    """The gate. Wrong or missing token: nothing happens and the caller is told."""
    if not registry.check(action.action_id, token):
        raise PermissionError(f"no valid approval token for {action.action_id}; action not executed")
    outbox.mkdir(parents=True, exist_ok=True)
    path = outbox / f"{employee_id}_{action.action_id}_{action.kind}.md"
    path.write_text(f"# {action.title}\n\n{action.body}\n", encoding="utf-8")
    return path

"""Template slots filled by code, never by the model.

Failure removed: a date or a credit count regenerated slightly wrong by a
language model. Every exact value in a drafted action comes from a typed
source object and is formatted by this module. The model writes prose around
the slots; it cannot write into them.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from pda.models import Certification, EmployeeProfile

_SLOT_RE = re.compile(r"\{\{([a-z_]+)\}\}")


class SlotError(KeyError):
    """A template slot was missing or a placeholder was left unfilled."""


def fill(template: str, slots: dict[str, str]) -> str:
    def _sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in slots:
            raise SlotError(f"no value for slot {key!r}")
        return slots[key]

    out = _SLOT_RE.sub(_sub, template)
    if _SLOT_RE.search(out):
        raise SlotError("unfilled placeholder remains after fill")
    return out


def renewal_slots(employee: EmployeeProfile, cert: Certification, today: date) -> dict[str, str]:
    remaining = max(0, cert.renewal_credits_required - cert.renewal_credits_earned)
    return {
        "employee_name": employee.name,
        "cert_name": cert.name,
        "issuer": cert.issuer,
        "expires_on": cert.expires_on.isoformat(),
        "days_to_expiry": str(cert.days_to_expiry(today)),
        "credits_required": str(cert.renewal_credits_required),
        "credits_earned": str(cert.renewal_credits_earned),
        "credits_remaining": str(remaining),
    }


def calendar_slots(start: date, weekly_hours: float, weeks: int) -> dict[str, str]:
    end = start + timedelta(weeks=weeks) - timedelta(days=1)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "weekly_hours": f"{weekly_hours:g}",
        "weeks": str(weeks),
        "total_hours": f"{weekly_hours * weeks:g}",
    }

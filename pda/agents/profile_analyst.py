"""Profile Analyst: read one employee's data, compute gaps in code, summarize.

The SQL is fixed and runs through the row-scoped connection, so the model
never writes a query and the agent cannot read anyone else's rows. Gap deltas
are plain integer comparisons against the role's required levels; the only
thing the model does is write one paragraph from values already computed.
"""
from __future__ import annotations

from datetime import date

from pda.guardrails.scoped_db import ScopedConnection
from pda.llm import LLM
from pda.models import Certification, EmployeeProfile, Gap
from pda.prompts import PROFILE_SUMMARY_SYSTEM


def load_profile(db: ScopedConnection) -> EmployeeProfile:
    row = db.query("SELECT * FROM employees WHERE employee_id = :employee_id")[0]
    skills = {r["skill"]: int(r["level"]) for r in
              db.query("SELECT skill, level FROM skills WHERE employee_id = :employee_id ORDER BY skill")}
    certs = [Certification(name=r["name"], issuer=r["issuer"], issued_on=date.fromisoformat(r["issued_on"]),
                           expires_on=date.fromisoformat(r["expires_on"]),
                           renewal_credits_required=int(r["renewal_credits_required"]),
                           renewal_credits_earned=int(r["renewal_credits_earned"]))
             for r in db.query("SELECT * FROM certifications WHERE employee_id = :employee_id ORDER BY expires_on")]
    return EmployeeProfile(employee_id=row["employee_id"], name=row["name"], role=row["role"],
                           department=row["department"], weekly_hours_limit=int(row["weekly_hours_limit"]),
                           skills=skills, certifications=certs, request=row["request"])


def snapshot_date(db: ScopedConnection) -> date:
    return date.fromisoformat(db.query_reference("SELECT snapshot_date FROM data_snapshot")[0]["snapshot_date"])


def taxonomy(db: ScopedConnection) -> set[str]:
    return {r["skill"] for r in db.query_reference("SELECT skill FROM skill_taxonomy")}


def compute_gaps(profile: EmployeeProfile, db: ScopedConnection) -> tuple[list[Gap], list[str]]:
    """Gaps and above-level skills, by integer comparison. No model involved."""
    req = {r["skill"]: int(r["required_level"]) for r in db.query_reference(
        "SELECT skill, required_level FROM role_requirements WHERE role = :role", {"role": profile.role})}
    gaps = [Gap(skill=s, current_level=profile.skills.get(s, 0), required_level=lvl)
            for s, lvl in sorted(req.items()) if profile.skills.get(s, 0) < lvl]
    above = [s for s, lvl in sorted(req.items()) if profile.skills.get(s, 0) > lvl]
    return gaps, above


def _facts(profile: EmployeeProfile, gaps: list[Gap], above: list[str], today: date) -> str:
    lines = [f"Name: {profile.name}", f"Role: {profile.role}", f"Department: {profile.department}",
             f"Weekly study limit: {profile.weekly_hours_limit} hours",
             "Gaps: " + ("; ".join(f"{g.skill} {g.current_level} -> {g.required_level}" for g in gaps) or "none"),
             "Above role level: " + (", ".join(above) or "none"),
             "Certifications: " + ("; ".join(
                 f"{c.name} expires {c.expires_on.isoformat()} ({c.days_to_expiry(today)} days), "
                 f"renewal credits {c.renewal_credits_earned}/{c.renewal_credits_required}"
                 for c in profile.certifications) or "none")]
    return "\n".join(lines)


def analyze(db: ScopedConnection, llm: LLM, today: date) -> tuple[EmployeeProfile, list[Gap], list[str], str]:
    profile = load_profile(db)
    gaps, above = compute_gaps(profile, db)
    summary = llm.complete("profile_summary", PROFILE_SUMMARY_SYSTEM, _facts(profile, gaps, above, today),
                           max_tokens=400)
    return profile, gaps, above, summary

"""Row-scoped, read-only database access bound to one employee.

Failure removed: a query, model-written or not, that reads another employee's
rows. In production this is a Snowflake role with a row access policy. Here it
is a wrapper around a read-only SQLite connection that injects the employee id
into every employee-scoped query and refuses any query that does not take it.

The model never sees this class. The Profile Analyst calls it with fixed SQL.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

EMPLOYEE_TABLES = {"employees", "skills", "certifications"}
REFERENCE_TABLES = {"skill_taxonomy", "role_requirements", "data_snapshot"}

_TABLE_RE = re.compile(r"\b(?:from|join)\s+([a-z_]+)", re.IGNORECASE)
_LITERAL_ID_RE = re.compile(r"'E\d{3}'")


class ScopeViolation(PermissionError):
    """The query tried to leave the employee's row scope."""


class ScopedConnection:
    def __init__(self, db_path: Path, employee_id: str) -> None:
        if not re.fullmatch(r"E\d{3}", employee_id):
            raise ScopeViolation(f"malformed employee id {employee_id!r}")
        self.employee_id = employee_id
        uri = f"file:{Path(db_path).as_posix()}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True)
        self._conn.row_factory = sqlite3.Row

    # ----- validation ------------------------------------------------------
    @staticmethod
    def _validate_common(sql: str) -> str:
        stripped = sql.strip().rstrip(";")
        if ";" in stripped:
            raise ScopeViolation("multiple statements are not allowed")
        if not stripped.lower().startswith("select"):
            raise ScopeViolation("only SELECT is allowed on a read-only scope")
        if _LITERAL_ID_RE.search(stripped):
            raise ScopeViolation("employee ids may not appear as literals; the scope supplies them")
        return stripped

    def query(self, sql: str, params: dict | None = None) -> list[sqlite3.Row]:
        """Employee-scoped read. ``sql`` must use ``:employee_id`` at least once."""
        stripped = self._validate_common(sql)
        tables = {t.lower() for t in _TABLE_RE.findall(stripped)}
        unknown = tables - EMPLOYEE_TABLES - REFERENCE_TABLES
        if unknown:
            raise ScopeViolation(f"tables outside the scope: {sorted(unknown)}")
        if ":employee_id" not in stripped:
            raise ScopeViolation("employee-scoped query must filter on :employee_id")
        params = dict(params or {})
        if "employee_id" in params:
            raise ScopeViolation("callers may not supply employee_id; the scope injects it")
        params["employee_id"] = self.employee_id
        return list(self._conn.execute(stripped, params))

    def query_reference(self, sql: str, params: dict | None = None) -> list[sqlite3.Row]:
        """Read from reference tables only (taxonomy, role requirements, snapshot)."""
        stripped = self._validate_common(sql)
        tables = {t.lower() for t in _TABLE_RE.findall(stripped)}
        if not tables or not tables <= REFERENCE_TABLES:
            raise ScopeViolation(f"reference queries may only read {sorted(REFERENCE_TABLES)}")
        return list(self._conn.execute(stripped, dict(params or {})))

    def close(self) -> None:
        self._conn.close()

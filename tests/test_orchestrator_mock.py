"""The ReAct loop in mock mode: sequencing enforced by code, recovery visible, packet frozen."""
from __future__ import annotations

from datetime import date

import pytest

from pda.config import load_settings
from pda.orchestrator import Orchestrator
from pda.state import FrozenPacketError
from tests.conftest import ROOT


def _orch(employee_id: str, tmp_path, **kw) -> Orchestrator:
    s = load_settings(mock=True)
    return Orchestrator(s, employee_id, run_log_path=tmp_path / f"{employee_id}.jsonl", **kw)


def test_e007_gathers_recovers_and_freezes(tmp_path):
    o = _orch("E007", tmp_path)
    result = o.run()
    actions = [h["action"] for h in result.history]
    assert actions == ["run_profile_analysis", "run_context_research", "run_resource_scout",
                       "retry_gathering", "freeze_packet", "finish"]
    failed = [h for h in result.history if h["observation"].startswith("FAILED")]
    assert len(failed) == 1 and failed[0]["action"] == "run_resource_scout"
    assert result.history[3]["observation"].startswith("retry 1/1")
    p = result.packet
    assert [g.skill for g in p.gaps] == ["Apache Spark", "Snowflake"]
    assert p.precondition.status == "ok" and 4 <= len(p.chunks) <= 8
    assert p.resources and all(r.verified for r in p.resources)
    assert p.memory.rejected and "Saturdays" in p.memory.rejected[0]
    assert "Priya Tanaka" in p.profile_summary and "Apache Spark 2 -> 3" in p.profile_summary
    assert result.packet_hash and result.status == "complete"
    assert result.escalations == []  # the retry succeeded, so nothing escalates on a clean E007 run
    assert (tmp_path / "E007.jsonl").read_text().count("react_step") == 6


def test_packet_is_immutable_after_freeze(tmp_path):
    o = _orch("E007", tmp_path)
    o.run()
    with pytest.raises(FrozenPacketError):
        o.store.update(profile_summary="tampered")
    view = o.store.view()
    view.gaps.clear()
    assert o.store.view().gaps, "a view is a copy; mutating it changes nothing in the store"


def test_phase_order_is_enforced_by_code_not_prompt(tmp_path):
    o = _orch("E007", tmp_path)
    assert "freeze_packet" not in o.allowed_actions()
    assert "run_resource_scout" in o.allowed_actions()
    assert o._dispatch("run_resource_scout").startswith("REJECTED"), "no gap list yet"


def test_no_role_doc_employee_gets_labeled_fallback(tmp_path):
    result = _orch("E011", tmp_path).run()
    assert result.packet.precondition.status == "no_role_doc"
    assert result.packet.chunks == []
    assert "missing_role_doc" in {e.reason for e in result.escalations}


def test_conflicting_docs_employee_escalates_to_ld(tmp_path):
    result = _orch("E010", tmp_path).run()
    ev = [e for e in result.escalations if e.reason == "conflicting_role_docs"]
    assert ev and ev[0].route_to == "ld"


def test_sensitive_request_triggers_classifier(tmp_path):
    result = _orch("E005", tmp_path).run()  # asks what a promotion would take
    assert "sensitive_topic" in {e.reason for e in result.escalations}


def test_stale_snapshot_when_clock_moves(tmp_path):
    result = _orch("E001", tmp_path, today=date(2026, 12, 1)).run()
    assert "stale_snapshot" in {e.reason for e in result.escalations}


def test_all_twelve_employees_reach_a_frozen_packet(tmp_path):
    for i in range(1, 13):
        r = _orch(f"E{i:03d}", tmp_path).run()
        assert r.packet_hash, f"E{i:03d} did not freeze"

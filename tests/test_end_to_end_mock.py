"""Whole system in mock mode: gather, freeze, synthesize, draft, confirm, execute."""
from __future__ import annotations

from pda import cli
from pda.config import load_settings
from pda.drafting import draft, execute
from pda.guardrails.approvals import ApprovalRegistry, HumanConfirmation
from pda.orchestrator import Orchestrator
from pda.tot import make_synthesizer


def _run(employee_id: str, tmp_path, **kw):
    s = load_settings(mock=True)
    o = Orchestrator(s, employee_id, synthesizer=make_synthesizer(s), drafter=draft,
                     run_log_path=tmp_path / f"{employee_id}.jsonl", **kw)
    return o.run(), s


def test_e007_end_to_end(tmp_path):
    result, _ = _run("E007", tmp_path)
    actions = [h["action"] for h in result.history]
    assert actions[-3:] == ["synthesize_plan", "draft_actions", "finish"]
    assert result.status == "complete" and result.plan.status == "complete"
    kinds = [d.kind for d in result.drafts]
    assert kinds == ["renewal_reminder", "calendar_block", "note"]
    renewal = result.drafts[0]
    # slots copied by code from the database row, verbatim
    assert renewal.slots["expires_on"] == "2026-10-01"
    assert renewal.slots["days_to_expiry"] == "30"
    assert renewal.slots["credits_remaining"] == "12"
    assert "expires on 2026-10-01, which is 30 days" in renewal.body
    assert "18 of the 30 renewal credits" in renewal.body
    assert all(d.status == "draft" for d in result.drafts)
    assert {e.reason for e in result.escalations} == {"external_side_effect", "thin_margin"}
    w = result.plan.winner
    assert set(w.gaps_addressed) == {"Apache Spark", "Snowflake"}
    assert set(w.resources_cited) <= {r.resource_id for r in result.packet.resources}
    assert "Saturday" not in w.content.replace("Avoid: Weekend study blocks on Saturdays", "")
    assert "R999" not in w.content


def test_execution_requires_a_human_token(tmp_path):
    result, _ = _run("E007", tmp_path)
    action = result.drafts[0]
    registry = ApprovalRegistry()
    outbox = tmp_path / "outbox"
    for forged in ("approved", "yes", "0123456789abcdef0123456789abcdef"):
        try:
            execute(action, forged, registry, outbox, "E007")
            assert False, "forged token executed an action"
        except PermissionError:
            pass
    assert not outbox.exists() or not any(outbox.iterdir())
    token = registry.issue(HumanConfirmation.from_prompt(action.action_id, "y"))
    path = execute(action, token, registry, outbox, "E007")
    assert path.exists() and "2026-10-01" in path.read_text(encoding="utf-8")
    try:
        execute(action, token, registry, outbox, "E007")
        assert False, "token was reusable"
    except PermissionError:
        pass


def test_cli_headless(capsys):
    code = cli.main(["--employee", "E007", "--mock", "--auto-approve-none"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Chosen plan" in out and "Runner-up" in out
    assert "left as draft" in out and "Approve" not in out
    assert "IMPORTANT SYSTEM NOTICE" not in out


def test_every_employee_completes(tmp_path):
    for i in range(1, 13):
        eid = f"E{i:03d}"
        result, _ = _run(eid, tmp_path)
        assert result.plan is not None, eid
        assert result.plan.status == "complete", f"{eid}: {result.plan.partial_reason}"
        assert result.drafts, eid

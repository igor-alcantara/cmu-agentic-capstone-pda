"""Tree of Thought: rules bound the set, the Critic only orders it."""
from __future__ import annotations

from datetime import date

import pytest

from pda.agents.critic import degenerate, rank
from pda.config import load_settings
from pda.guardrails.budget import Budget
from pda.llm import MockLLM
from pda.mock_handlers import register_all
from pda.models import PlanBranch
from pda.orchestrator import Orchestrator
from pda.tot import hard_check, make_synthesizer


@pytest.fixture(scope="module")
def frozen_e007(tmp_path_factory):
    s = load_settings(mock=True)
    o = Orchestrator(s, "E007", run_log_path=tmp_path_factory.mktemp("runs") / "E007.jsonl")
    o.run()
    return o.store.view()


def _branch(**kw) -> PlanBranch:
    base = dict(branch_id="x", depth=3, parent_id=None,
                content="a plan with more than enough words in it to clear the degenerate floor comfortably",
                gaps_addressed=["Apache Spark", "Snowflake"], resources_cited=["R009", "R021"], weekly_hours=5,
                schedule_start=date(2026, 9, 1), schedule_end=date(2026, 11, 30))
    base.update(kw)
    return PlanBranch(**base)


def test_hard_checks_name_each_failure(frozen_e007):
    p = frozen_e007
    assert hard_check(_branch(), p, 3) == []
    assert "gaps not addressed: Snowflake" in hard_check(_branch(gaps_addressed=["Apache Spark"]), p, 3)
    assert any("R999" in r for r in hard_check(_branch(resources_cited=["R009", "R999"]), p, 3))
    assert any("weekly hours 6" in r for r in hard_check(_branch(weekly_hours=6), p, 3))
    assert any("schedule" in r for r in hard_check(_branch(schedule_start=None, schedule_end=None), p, 3))
    assert any("schedule" in r for r in hard_check(_branch(schedule_end=date(2028, 1, 1)), p, 3))
    assert "no resources cited at a stage that requires them" in hard_check(_branch(resources_cited=[]), p, 2)


def test_degenerate_floor_is_only_a_floor():
    assert degenerate(_branch(content="ok"))
    assert not degenerate(_branch())


def test_beam_search_keeps_two_and_critic_never_sees_rejected(frozen_e007, tmp_path):
    s = load_settings(mock=True)
    budget = Budget(100, 500_000, 300)
    llm = MockLLM(budget)
    register_all(llm)
    o = Orchestrator(s, "E007", llm=llm, budget=budget, run_log_path=tmp_path / "E007.jsonl")
    o.run()
    plan = make_synthesizer(s)(o.store.view(), llm, budget, o.store, o.today)
    assert plan.status == "complete" and plan.winner is not None
    assert hard_check(plan.winner, o.store.view(), 3) == []
    depths = [e for e in o.store.steps if e["kind"] == "tot_depth"]
    assert [d["depth"] for d in depths] == [1, 2, 3]
    assert all(len(d["kept"]) == 2 for d in depths)
    assert all(d["rejected"] >= 1 for d in depths), "each depth has a flawed sibling the rules must catch"
    critic_prompts = "\n".join(u for t, _, u in llm.calls if t == "critic")
    assert "R999" not in critic_prompts and "strategy: focus" not in critic_prompts
    assert plan.close_call and plan.runner_up is not None
    assert plan.winner.critic_rank == 1 and plan.runner_up.critic_rank == 2
    planner_calls = sum(1 for t, _, _ in llm.calls if t == "planner")
    assert planner_calls == 1 + 2 + 2  # one root, then two parents per depth


def test_critic_tolerates_garbage_and_keeps_order():
    llm = MockLLM(Budget(10, 10_000, 60))
    llm.register("critic", lambda s, u: "I refuse to answer in JSON.")
    a, b = _branch(branch_id="a"), _branch(branch_id="b")
    ranked, verdict, ok = rank("packet", [a, b], 3, llm)
    assert not ok and verdict == "clear_win"
    assert [r.branch_id for r in ranked] == ["a", "b"]
    assert "unparseable" in ranked[0].critic_rationale


def test_critic_partial_ranking_is_completed():
    llm = MockLLM(Budget(10, 10_000, 60))
    llm.register("critic", lambda s, u: '{"ranking": [1], "rationales": {"1": "best"}, "verdict": "close_call"}')
    a, b, c = _branch(branch_id="a"), _branch(branch_id="b"), _branch(branch_id="c")
    ranked, verdict, ok = rank("packet", [a, b, c], 3, llm)
    assert ok and verdict == "close_call"
    assert [r.branch_id for r in ranked] == ["b", "a", "c"]


def test_labeled_partial_when_nothing_passes(frozen_e007, tmp_path):
    s = load_settings(mock=True)
    budget = Budget(100, 500_000, 300)
    llm = MockLLM(budget)
    register_all(llm)
    llm.register("planner", lambda sys_, u: '[{"content": "a long enough plan that ignores every gap on purpose", '
                                            '"gaps_addressed": [], "resources_cited": [], "weekly_hours": 5}]')
    o = Orchestrator(s, "E007", llm=llm, budget=budget, run_log_path=tmp_path / "E007.jsonl")
    o.run()
    plan = make_synthesizer(s)(o.store.view(), llm, budget, o.store, o.today)
    assert plan.status == "partial" and "depth 1" in plan.partial_reason
    assert plan.winner is None and not any(t == "critic" for t, _, _ in llm.calls)

"""Offline autoloop planner tests — no network, no sessions started."""

from __future__ import annotations

import json

import pytest

from agent_harness.cli import main
from agent_harness.loop import (
    MAX_ITERATIONS_CAP,
    autoprompt,
    build_loop_plan,
)


def test_plan_is_bounded_by_max_iterations() -> None:
    plan = build_loop_plan("do a thing", max_iterations=4)
    assert len(plan.iterations) == 4
    assert [it.index for it in plan.iterations] == [0, 1, 2, 3]


def test_plan_is_deterministic() -> None:
    """Same spec must yield an identical plan — no clock, no randomness.

    Session ids derive from a hash of task+index precisely so a plan can be asserted on
    and diffed. A planner seeded by time would be untestable and would churn on re-run.
    """
    assert build_loop_plan("same task").to_json() == build_loop_plan("same task").to_json()


def test_different_tasks_get_different_sessions() -> None:
    a = build_loop_plan("task a").iterations[0].session_id
    b = build_loop_plan("task b").iterations[0].session_id
    assert a != b


def test_iterations_within_a_plan_get_distinct_sessions() -> None:
    """Ephemeral means each iteration is its own session, not a resumed one."""
    ids = [it.session_id for it in build_loop_plan("t", max_iterations=5).iterations]
    assert len(set(ids)) == 5


def test_live_execution_is_refused() -> None:
    """v0.x plans autoloops; it does not run them. Matches build_spawn_plan."""
    with pytest.raises(NotImplementedError, match="not implemented in v0.x"):
        build_loop_plan("t", dry_run=False)


@pytest.mark.parametrize("bad", [0, -1, MAX_ITERATIONS_CAP + 1])
def test_max_iterations_is_validated(bad: int) -> None:
    """Unbounded, or absurdly bounded, is an unbounded spend. Refuse both."""
    with pytest.raises(ValueError, match="max_iterations"):
        build_loop_plan("t", max_iterations=bad)


def test_empty_task_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        build_loop_plan("   ")


def test_idle_stop_that_could_never_fire_is_refused() -> None:
    """A stop condition that cannot trigger is worse than none — it reads as protection."""
    with pytest.raises(ValueError, match="could never fire"):
        build_loop_plan("t", max_iterations=3, stop_after_idle=9)


def test_first_prompt_is_the_task_verbatim() -> None:
    assert autoprompt("build the thing", 0) == "build the thing"


def test_resumed_prompt_restates_task_and_forbids_borrowed_credit() -> None:
    """An ephemeral session has no memory, so the prompt must carry the task itself.

    It must also stop the session claiming the previous iteration's work: without an
    explicit instruction, a resumed session tends to trust the carried summary and
    re-report success it never observed.
    """
    p = autoprompt("build the thing", 2, last_outcome="added module X")
    assert "build the thing" in p
    assert "added module X" in p
    assert "did not perform that work" in p
    assert "verify" in p.lower()


def test_resumed_prompt_handles_missing_outcome() -> None:
    p = autoprompt("t", 1, last_outcome=None)
    assert "(none reported)" in p


def test_negative_index_is_refused() -> None:
    with pytest.raises(ValueError, match="index must be >= 0"):
        autoprompt("t", -1)


def test_plan_declares_its_stop_conditions() -> None:
    """Never-silent: a loop that stops without saying why looks like a crash."""
    plan = build_loop_plan("t")
    assert "max-iterations" in plan.stop_conditions
    assert "converged" in plan.stop_conditions


def test_plan_is_offline() -> None:
    plan = build_loop_plan("t")
    assert plan.network is False
    assert plan.mode == "dry-run"


def test_cli_loop_renders(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["loop", "--task", "ship it", "--dry-run", "--max-iterations", "2"])
    assert code == 0
    out = capsys.readouterr().out
    assert "autoloop plan (dry-run)" in out
    assert "ship it" in out


def test_cli_loop_json_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["loop", "--task", "ship it", "--dry-run", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "dry-run"
    assert data["network"] is False
    assert len(data["iterations"]) == data["max_iterations"]


def test_cli_loop_without_dry_run_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["loop", "--task", "ship it"])
    assert code == 2
    assert "not implemented in v0.x" in capsys.readouterr().err

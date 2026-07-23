"""Offline tests for the autodev supervisor loop.

Nothing here forks a process, touches the network, or talks to a real bus: the
runner is injected, so every provider and every `coop` call is a fake.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from agent_harness.autoprompt import build_autoprompt, handoff_path_for
from agent_harness.cli import main
from agent_harness.coop import (
    LEASE_HELD,
    MAX_BODY,
    CoopClient,
    RunResult,
    clamp_body,
    parse_leases,
)
from agent_harness.providers import CLAUDE, GROK, Budget, NoProviderAvailable, route
from agent_harness.supervisor import (
    ESCALATED,
    FAILED,
    OK,
    PLANNED,
    SKIPPED_HELD,
    Supervisor,
    summarise,
)
from agent_harness.units import Backlog, WorkUnit, dedupe_by_key, load_units


class FakeRunner:
    """Records argv and replays scripted results."""

    def __init__(self, results: dict[str, RunResult] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.results = results or {}
        self.default = RunResult(0, "ok", "")

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> RunResult:
        argv = list(argv)
        self.calls.append(argv)
        for needle, result in self.results.items():
            if needle in " ".join(argv):
                return result
        return self.default

    def argv_for(self, needle: str) -> list[list[str]]:
        return [c for c in self.calls if needle in " ".join(c)]


def make_unit(**overrides: object) -> WorkUnit:
    base: dict[str, object] = {
        "uid": "u1",
        "repo": "agent-harness",
        "component": "agent_harness/",
        "task": "Do the thing.",
        "issue": 24,
    }
    base.update(overrides)
    return WorkUnit(**base)  # type: ignore[arg-type]


def make_supervisor(
    runner: FakeRunner,
    tmp_path: Path,
    *,
    units: list[WorkUnit] | None = None,
    live: bool = True,
    failure_budget: int = 3,
) -> Supervisor:
    return Supervisor(
        coop=CoopClient(runner=runner, agent="claude", home=str(tmp_path / "coop")),
        backlog=Backlog(units=units or [make_unit()]),
        handoff_dir=tmp_path / "handoff",
        runner=runner,
        available=["claude", "grok"],
        live=live,
        failure_budget=failure_budget,
    )


# -- units --------------------------------------------------------------------


def test_unit_rejects_empty_task() -> None:
    with pytest.raises(ValueError, match="non-empty task"):
        make_unit(task="   ")


def test_unit_rejects_unknown_lane() -> None:
    with pytest.raises(ValueError, match="lane must be one of"):
        make_unit(lane="turbo")


def test_unit_key_is_lease_key() -> None:
    assert make_unit().key == "agent-harness:agent_harness/"


def test_dedupe_collapses_same_component() -> None:
    a = make_unit(uid="a")
    b = make_unit(uid="b")
    c = make_unit(uid="c", component="docs/")
    assert [u.uid for u in dedupe_by_key([a, b, c])] == ["a", "c"]


def test_load_units_accepts_both_shapes(tmp_path: Path) -> None:
    payload = [make_unit().to_dict()]
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(payload), encoding="utf-8")
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"units": payload}), encoding="utf-8")
    assert load_units(bare)[0].uid == "u1"
    assert load_units(wrapped)[0].uid == "u1"


def test_load_units_ignores_unknown_keys(tmp_path: Path) -> None:
    payload = [{**make_unit().to_dict(), "nonsense": 1}]
    path = tmp_path / "u.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_units(path)[0].uid == "u1"


# -- coop adapter --------------------------------------------------------------


def test_parse_leases_reads_real_output() -> None:
    text = (
        "grok     agent-harness:agent_harness/  expires_epoch=1784787681\n"
        "claude   agent-coop:plans/x.yml  expires_epoch=1784787355\n"
        "garbage line\n"
    )
    leases = parse_leases(text)
    assert [lease.agent for lease in leases] == ["grok", "claude"]
    assert leases[0].key == "agent-harness:agent_harness/"
    assert leases[0].expires_epoch == 1784787681


def test_claim_returns_false_on_exit_three() -> None:
    runner = FakeRunner({"lease claim": RunResult(LEASE_HELD, "", "held")})
    client = CoopClient(runner=runner, agent="claude")
    assert client.claim("repo", "comp") is False


def test_claim_true_on_success() -> None:
    runner = FakeRunner({"lease claim": RunResult(0, "claimed", "")})
    assert CoopClient(runner=runner, agent="claude").claim("repo", "comp") is True


def test_clamp_body_respects_bus_limit() -> None:
    body = clamp_body("x" * 900)
    assert len(body) <= MAX_BODY


def test_clamp_body_collapses_whitespace() -> None:
    assert clamp_body("a\n\n  b   c") == "a b c"


def test_message_rejects_unknown_type() -> None:
    client = CoopClient(runner=FakeRunner(), agent="claude")
    with pytest.raises(ValueError, match="unknown message type"):
        client.message(to="all", type="gossip", body="hi")


def test_message_truncates_rather_than_failing() -> None:
    runner = FakeRunner()
    CoopClient(runner=runner, agent="claude").message(
        to="all", type="status", body="y" * 4000
    )
    sent = runner.argv_for("msg")[0]
    body = sent[sent.index("--body") + 1]
    assert len(body) <= MAX_BODY


def test_held_by_others_excludes_self() -> None:
    text = (
        "grok    repo:a  expires_epoch=1\n"
        "claude  repo:b  expires_epoch=2\n"
    )
    runner = FakeRunner({"lease list": RunResult(0, text, "")})
    client = CoopClient(runner=runner, agent="claude")
    assert client.held_by_others() == {"repo:a"}


# -- providers -----------------------------------------------------------------


def test_route_prefers_grok_for_implementation() -> None:
    # Operator policy: grok implements, claude plans and verifies.
    assert route(lane="build", role="implement", available=["claude", "grok"]).name == "grok"


def test_route_prefers_claude_for_plan_and_verify() -> None:
    assert route(lane="build", role="plan", available=["claude", "grok"]).name == "claude"
    assert route(lane="build", role="verify", available=["claude", "grok"]).name == "claude"


def test_stage_preference_yields_to_availability() -> None:
    # Preference is not a requirement: if grok is absent, claude still implements.
    assert route(lane="build", role="implement", available=["claude"]).name == "claude"


def test_route_falls_back_when_claude_absent() -> None:
    assert route(lane="build", available=["grok"]).name == "grok"


def test_route_respects_lane_capability() -> None:
    # grok does not serve the flagship lane; with claude absent this must escalate
    # rather than silently downgrade the tier.
    with pytest.raises(NoProviderAvailable):
        route(lane="flagship", available=["grok"])


def test_route_skips_exhausted_budget() -> None:
    chosen = route(
        lane="build",
        available=["claude", "grok"],
        budgets={"claude": Budget(remaining=0)},
    )
    assert chosen.name == "grok"


def test_route_pinned_provider_must_be_available() -> None:
    with pytest.raises(NoProviderAvailable, match="not installed"):
        route(lane="build", pinned="grok", available=["claude"])


def test_build_argv_is_single_shot() -> None:
    assert CLAUDE.build_argv("hi") == ["claude", "-p", "hi", "--output-format", "json"]
    assert GROK.build_argv("hi")[:3] == ["grok", "-p", "hi"]


# -- autoprompt ----------------------------------------------------------------


def test_autoprompt_carries_the_discipline(tmp_path: Path) -> None:
    prompt = build_autoprompt(
        make_unit(), handoff_dir=tmp_path, agent_name="claude", coop_home="/x/.coop"
    )
    assert "exactly ONE unit" in prompt
    assert "exiting **3**" in prompt
    assert "Do not retry, do not steal" in prompt
    assert "bash scripts/local-ci.sh" in prompt
    assert str(handoff_path_for(make_unit(), tmp_path)) in prompt
    assert "AGENT_COOP_AGENT=claude" in prompt


def test_autoprompt_includes_prior_error_on_retry(tmp_path: Path) -> None:
    prompt = build_autoprompt(
        make_unit(),
        handoff_dir=tmp_path,
        agent_name="claude",
        attempt=2,
        prior_error="gate failed",
    )
    assert "attempt 2" in prompt
    assert "gate failed" in prompt


def test_autoprompt_is_bounded(tmp_path: Path) -> None:
    prompt = build_autoprompt(
        make_unit(task="z" * 50_000), handoff_dir=tmp_path, agent_name="claude"
    )
    assert len(prompt) <= 8000
    assert "truncated" in prompt


# -- supervisor ----------------------------------------------------------------


def test_dry_run_claims_nothing_and_spawns_nothing(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path, live=False)
    outcomes = sup.run_once()
    assert [o.status for o in outcomes] == [PLANNED]
    assert runner.argv_for("lease claim") == []
    assert runner.argv_for("-p") == []


def test_live_success_claims_spawns_and_releases(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    outcomes = sup.run_once()
    assert [o.status for o in outcomes] == [OK]
    assert runner.argv_for("lease claim")
    assert runner.argv_for("lease release")
    spawned = runner.argv_for("--output-format")
    assert spawned and spawned[0][0] == "claude"


def test_held_lease_backs_off_without_spawning(tmp_path: Path) -> None:
    runner = FakeRunner({"lease claim": RunResult(LEASE_HELD, "", "held")})
    sup = make_supervisor(runner, tmp_path)
    outcomes = sup.run_once()
    assert [o.status for o in outcomes] == [SKIPPED_HELD]
    # Never spawn behind a lease we do not hold, and never release it either.
    assert runner.argv_for("--output-format") == []
    assert runner.argv_for("lease release") == []


def test_failure_escalates_only_after_budget(tmp_path: Path) -> None:
    runner = FakeRunner({"--output-format": RunResult(1, "", "gate failed")})
    sup = make_supervisor(runner, tmp_path, failure_budget=2)

    first = sup.run_once()
    assert [o.status for o in first] == [FAILED]

    second = sup.run_once()
    assert [o.status for o in second] == [ESCALATED]

    # Escalation posts a block message naming the unit.
    blocks = [c for c in runner.calls if "--type" in c and "block" in c]
    assert blocks, "expected a block message on escalation"
    assert any("u1" in " ".join(c) for c in blocks)


def test_escalated_unit_is_not_respawned(tmp_path: Path) -> None:
    runner = FakeRunner({"--output-format": RunResult(1, "", "boom")})
    sup = make_supervisor(runner, tmp_path, failure_budget=1)
    sup.run_once()
    spawns_after_escalation = len(runner.argv_for("--output-format"))
    sup.run_once()
    assert len(runner.argv_for("--output-format")) == spawns_after_escalation


def test_handoff_stub_written_when_session_leaves_none(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    sup.run_once()
    handoff = tmp_path / "handoff" / "u1.md"
    assert handoff.is_file()
    assert "handoff: u1" in handoff.read_text(encoding="utf-8")


def test_real_handoff_is_not_overwritten(tmp_path: Path) -> None:
    handoff_dir = tmp_path / "handoff"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / "u1.md").write_text("written by the session", encoding="utf-8")
    sup = make_supervisor(FakeRunner(), tmp_path)
    sup.run_once()
    assert (handoff_dir / "u1.md").read_text(encoding="utf-8") == "written by the session"


def test_bus_message_is_a_pointer_not_the_payload(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    sup.run_once()
    msgs = runner.argv_for("msg")
    assert msgs
    body = msgs[0][msgs[0].index("--body") + 1]
    assert "handoff:" in body
    assert "u1.md" in body


def test_run_stops_when_backlog_is_exhausted(tmp_path: Path) -> None:
    runner = FakeRunner({"--output-format": RunResult(1, "", "boom")})
    sup = make_supervisor(runner, tmp_path, failure_budget=1)
    passes = sup.run(max_iterations=10)
    # Unit escalates on pass 1, so pass 2 finds nothing pending and the loop ends.
    assert len(passes) == 1


def test_dry_run_survives_no_provider_installed(tmp_path: Path) -> None:
    """CI has neither provider CLI installed; planning must still succeed quietly."""
    runner = FakeRunner()
    sup = Supervisor(
        coop=CoopClient(runner=runner, agent="claude"),
        backlog=Backlog(units=[make_unit()]),
        handoff_dir=tmp_path / "handoff",
        runner=runner,
        available=[],
        live=False,
    )
    outcomes = sup.run_once()
    assert [o.status for o in outcomes] == [PLANNED]
    assert "unroutable" in outcomes[0].detail
    # Planning must never touch the bus.
    assert runner.argv_for("msg") == []


def test_no_provider_escalates(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = Supervisor(
        coop=CoopClient(runner=runner, agent="claude"),
        backlog=Backlog(units=[make_unit(lane="flagship")]),
        handoff_dir=tmp_path / "handoff",
        runner=runner,
        available=["grok"],
        live=True,
    )
    outcomes = sup.run_once()
    assert outcomes[0].status == "no-provider"


def test_summarise_counts_statuses() -> None:
    sup_out = [[type("O", (), {"status": "ok"})(), type("O", (), {"status": "ok"})()]]
    assert summarise(sup_out) == {"ok": 2}


# -- cli -----------------------------------------------------------------------


def _write_backlog(tmp_path: Path) -> Path:
    path = tmp_path / "units.json"
    path.write_text(json.dumps([make_unit().to_dict()]), encoding="utf-8")
    return path


def test_cli_loop_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_backlog(tmp_path)
    code = main(["loop", "--units", str(path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "autodev loop (dry-run)" in out
    assert "planned" in out


def test_cli_loop_rejects_bad_budget(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_backlog(tmp_path)
    code = main(["loop", "--units", str(path), "--budget", "claude=lots"])
    assert code == 2
    assert "not a number" in capsys.readouterr().err


def test_cli_loop_missing_backlog(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["loop", "--units", str(tmp_path / "nope.json")])
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_cli_loop_empty_backlog(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    code = main(["loop", "--units", str(path)])
    assert code == 0
    assert "backlog is empty" in capsys.readouterr().out


# -- enqueue / status board ----------------------------------------------------


def test_enqueue_appends_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "backlog.json"
    code = main(
        [
            "enqueue", "--units", str(path), "--uid", "a1",
            "--repo", "r", "--component", "c/", "--task", "do it",
        ]
    )
    assert code == 0
    assert [u.uid for u in load_units(path)] == ["a1"]


def test_enqueue_rejects_duplicate_uid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "backlog.json"
    args = [
        "enqueue", "--units", str(path), "--uid", "a1",
        "--repo", "r", "--component", "c/", "--task", "do it",
    ]
    assert main(args) == 0
    assert main(args) == 2
    assert "already contains" in capsys.readouterr().err


def test_enqueue_preserves_wrapped_shape(tmp_path: Path) -> None:
    path = tmp_path / "backlog.json"
    path.write_text(json.dumps({"units": [make_unit().to_dict()]}), encoding="utf-8")
    main(
        [
            "enqueue", "--units", str(path), "--uid", "a2",
            "--repo", "r", "--component", "c/", "--task", "do it",
        ]
    )
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(reloaded, dict) and "units" in reloaded


def test_status_board_renders(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_backlog(tmp_path)
    code = main(["status", "--units", str(path), "--no-coop"])
    assert code == 0
    out = capsys.readouterr().out
    assert "supervisor board" in out
    assert "u1" in out
    assert "pending" in out


def test_status_board_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_backlog(tmp_path)
    assert main(["status", "--units", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["units"][0]["uid"] == "u1"


def test_status_board_empty_backlog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["status", "--no-coop"]) == 0
    assert "backlog empty" in capsys.readouterr().out


# -- staged pipeline -----------------------------------------------------------


def test_unit_runs_plan_implement_verify_in_order(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    outcomes = sup.run_once()
    assert outcomes[0].status == OK
    # One ephemeral session per stage, in order, with the policy providers.
    assert outcomes[0].detail == "plan:claude -> implement:grok -> verify:claude"
    assert len(runner.argv_for("--output-format")) == 3


def test_stage_prompts_differ_and_plan_forbids_edits(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    sup.run_once()
    prompts = [c[2] for c in runner.argv_for("--output-format")]
    assert "Your stage: PLAN" in prompts[0]
    assert "Do not modify, create, or delete any code" in prompts[0]
    assert "Your stage: IMPLEMENT" in prompts[1]
    assert "Your stage: VERIFY" in prompts[2]


def test_plan_stage_does_not_ask_for_the_gate(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path)
    sup.run_once()
    plan_prompt = runner.argv_for("--output-format")[0][2]
    assert "you changed nothing" in plan_prompt


def test_failed_plan_aborts_remaining_stages(tmp_path: Path) -> None:
    runner = FakeRunner({"Your stage: PLAN": RunResult(1, "", "cannot plan")})
    sup = make_supervisor(runner, tmp_path)
    outcomes = sup.run_once()
    assert outcomes[0].status == FAILED
    # Implementing an unplanned unit is wasted spend.
    assert len(runner.argv_for("--output-format")) == 1


def test_single_stage_unit_is_honoured(tmp_path: Path) -> None:
    runner = FakeRunner()
    sup = make_supervisor(runner, tmp_path, units=[make_unit(stages=("implement",))])
    outcomes = sup.run_once()
    assert outcomes[0].detail == "implement:grok"
    assert len(runner.argv_for("--output-format")) == 1


def test_unknown_stage_rejected() -> None:
    with pytest.raises(ValueError, match="unknown stage"):
        make_unit(stages=("ponder",))

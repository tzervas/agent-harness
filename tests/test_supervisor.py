"""Autodev supervisor tests — mock provider only (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_harness.cli import main
from agent_harness.supervisor import Supervisor, SupervisorConfig
from agent_harness.unit_of_work import new_unit


def test_enqueue_and_once_done(tmp_path: Path) -> None:
    ptr = tmp_path / "plan.md"
    ptr.write_text("# plan\ndo the thing\n", encoding="utf-8")
    sup = Supervisor(
        SupervisorConfig(home=tmp_path / "h", claim_leases=False, mock_fail_times=0)
    )
    unit = sup.enqueue(
        title="demo",
        pointer=str(ptr),
        provider="mock",
        component="demo",
    )
    assert unit.state == "queued"
    report = sup.tick()
    assert report.acted is True
    assert report.result == "done"
    loaded = sup.store.load(unit.id)
    assert loaded is not None
    assert loaded.state == "done"


def test_failure_budget_escalates(tmp_path: Path) -> None:
    ptr = tmp_path / "plan.md"
    ptr.write_text("x\n", encoding="utf-8")
    sup = Supervisor(
        SupervisorConfig(
            home=tmp_path / "h",
            claim_leases=False,
            mock_fail_times=99,
        )
    )
    unit = sup.enqueue(
        title="flaky",
        pointer=str(ptr),
        provider="mock",
        max_attempts=2,
    )
    r1 = sup.tick()
    assert r1.result == "retry"
    r2 = sup.tick()
    assert r2.result == "escalated"
    loaded = sup.store.load(unit.id)
    assert loaded is not None
    assert loaded.state == "escalated"


def test_unit_prompt_contains_pointer() -> None:
    u = new_unit(title="t", pointer="/tmp/p.md", provider="mock")
    text = u.render_prompt()
    assert "/tmp/p.md" in text
    assert u.id in text


def test_cli_enqueue_loop_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ptr = tmp_path / "p.md"
    ptr.write_text("hi\n", encoding="utf-8")
    home = str(tmp_path / "home")
    code = main(
        [
            "enqueue",
            "--home",
            home,
            "--title",
            "cli-demo",
            "--pointer",
            str(ptr),
            "--provider",
            "mock",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "enqueued" in out

    code = main(["loop", "--home", home, "--once", "--no-lease"])
    assert code == 0
    out = capsys.readouterr().out
    assert "done" in out or "result=" in out

    code = main(["status", "--home", home])
    assert code == 0
    out = capsys.readouterr().out
    assert "supervisor" in out or "queued" in out

"""Offline CLI tests — no network."""

from __future__ import annotations

import re

import pytest

from agent_harness import read_version
from agent_harness.cli import main
from agent_harness.spawn import build_spawn_plan


def test_version_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["version"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out
    assert "dev" in out or re.match(r"\d+\.\d+\.\d+", out)


def test_read_version_matches_cli(capsys: pytest.CaptureFixture[str]) -> None:
    main(["version"])
    out = capsys.readouterr().out.strip()
    assert out == read_version()


def test_spawn_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["spawn", "--issue", "3", "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "spawn plan (dry-run)" in out
    assert "#3" in out
    assert "network:      false" in out
    assert "bash scripts/local-ci.sh" in out


def test_spawn_requires_positive_issue(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["spawn", "--issue", "0", "--dry-run"])
    assert code == 2
    err = capsys.readouterr().err
    assert "positive" in err


def test_spawn_without_dry_run_not_implemented(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["spawn", "--issue", "1"])
    assert code == 2
    err = capsys.readouterr().err
    assert "dry-run" in err


def test_build_spawn_plan_dict() -> None:
    plan = build_spawn_plan(5, dry_run=True)
    d = plan.to_dict()
    assert d["issue"] == 5
    assert d["network"] is False
    assert d["mode"] == "dry-run"


def test_doctor_runs(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["doctor"])
    # May fail checks if cwd lacks VERSION; still must be 0 or 1.
    assert code in (0, 1)
    out = capsys.readouterr().out
    assert "doctor (offline)" in out
    assert "python>=3.14" in out

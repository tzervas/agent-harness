"""Provider adapters: mock | claude | grok ephemeral sessions."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_harness.unit_of_work import Provider, UnitOfWork


@dataclass
class SessionResult:
    ok: bool
    provider: Provider
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    pid: int | None = None


class ProviderDriver(Protocol):
    name: Provider

    def run(self, unit: UnitOfWork, *, work_dir: Path, timeout_s: int) -> SessionResult: ...


@dataclass
class MockProvider:
    """Deterministic offline provider for tests and dry loops."""

    name: Provider = "mock"
    fail_times: int = 0
    _calls: int = 0

    def run(self, unit: UnitOfWork, *, work_dir: Path, timeout_s: int) -> SessionResult:
        del timeout_s
        self._calls += 1
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / "mock-result.txt"
        body = f"mock ok unit={unit.id} pointer={unit.pointer} call={self._calls}\n"
        out.write_text(body, encoding="utf-8")
        if self._calls <= self.fail_times:
            return SessionResult(
                ok=False,
                provider="mock",
                exit_code=1,
                stdout="",
                stderr=f"mock intentional fail #{self._calls}",
                duration_s=0.01,
            )
        return SessionResult(
            ok=True,
            provider="mock",
            exit_code=0,
            stdout=body,
            stderr="",
            duration_s=0.01,
        )


@dataclass
class ClaudeProvider:
    """Ephemeral Claude Code session via ``claude -p`` (print / non-interactive)."""

    name: Provider = "claude"
    binary: str = "claude"
    bare: bool = True

    def run(self, unit: UnitOfWork, *, work_dir: Path, timeout_s: int) -> SessionResult:
        exe = shutil.which(self.binary)
        if not exe:
            return SessionResult(
                ok=False,
                provider="claude",
                exit_code=127,
                stderr=f"{self.binary} not on PATH",
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = work_dir / "prompt.md"
        prompt_path.write_text(unit.render_prompt(), encoding="utf-8")
        argv = [exe, "-p", unit.render_prompt()]
        if self.bare:
            argv.append("--bare")
        # Prefer cwd of pointer's parent when local path
        cwd = work_dir
        ptr = Path(unit.pointer)
        if ptr.is_file():
            cwd = ptr.parent
        t0 = time.time()
        try:
            cp = subprocess.run(
                argv,
                check=False,
                text=True,
                capture_output=True,
                cwd=str(cwd),
                timeout=timeout_s,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            return SessionResult(
                ok=False,
                provider="claude",
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\ntimeout",
                duration_s=time.time() - t0,
            )
        (work_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
        (work_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
        return SessionResult(
            ok=cp.returncode == 0,
            provider="claude",
            exit_code=int(cp.returncode),
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
            duration_s=time.time() - t0,
        )


@dataclass
class GrokProvider:
    """Ephemeral Grok session via ``grok -p`` / ``--single``."""

    name: Provider = "grok"
    binary: str = "grok"

    def run(self, unit: UnitOfWork, *, work_dir: Path, timeout_s: int) -> SessionResult:
        exe = shutil.which(self.binary)
        if not exe:
            return SessionResult(
                ok=False,
                provider="grok",
                exit_code=127,
                stderr=f"{self.binary} not on PATH",
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = work_dir / "prompt.md"
        prompt_path.write_text(unit.render_prompt(), encoding="utf-8")
        # grok: -p/--single PROMPT or --prompt-file
        argv = [exe, "--prompt-file", str(prompt_path)]
        cwd = work_dir
        ptr = Path(unit.pointer)
        if ptr.is_file():
            cwd = ptr.parent
        t0 = time.time()
        try:
            cp = subprocess.run(
                argv,
                check=False,
                text=True,
                capture_output=True,
                cwd=str(cwd),
                timeout=timeout_s,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            return SessionResult(
                ok=False,
                provider="grok",
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\ntimeout",
                duration_s=time.time() - t0,
            )
        (work_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
        (work_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
        return SessionResult(
            ok=cp.returncode == 0,
            provider="grok",
            exit_code=int(cp.returncode),
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
            duration_s=time.time() - t0,
        )


def get_provider(name: Provider, *, mock_fail_times: int = 0) -> ProviderDriver:
    if name == "mock":
        return MockProvider(fail_times=mock_fail_times)
    if name == "claude":
        return ClaudeProvider()
    if name == "grok":
        return GrokProvider()
    msg = f"unknown provider: {name}"
    raise ValueError(msg)

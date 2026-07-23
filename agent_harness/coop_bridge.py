"""Drive agent-coop CLIs without reimplementing the bus (ADR-0002).

stdlib only — shells out to ``coop-msg`` / ``coop-inbox`` / ``coop-lease`` /
``coop-status`` when present. Tests inject a fake runner.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _default_runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        check=False,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
        timeout=60,
    )


@dataclass
class CoopBridge:
    """Thin adapter over installed agent-coop console scripts."""

    agent: str = "grok"
    home: str | None = None
    runner: Runner = _default_runner

    def available(self) -> bool:
        return shutil.which("coop-msg") is not None

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["AGENT_COOP_AGENT"] = self.agent
        if self.home:
            env["AGENT_COOP_HOME"] = self.home
        return env

    def _run(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        # Prefer injecting env via runner env; default runner uses os.environ
        # so set temporarily when home/agent override.
        old_agent = os.environ.get("AGENT_COOP_AGENT")
        old_home = os.environ.get("AGENT_COOP_HOME")
        try:
            os.environ["AGENT_COOP_AGENT"] = self.agent
            if self.home:
                os.environ["AGENT_COOP_HOME"] = self.home
            return self.runner(argv)
        finally:
            if old_agent is None:
                os.environ.pop("AGENT_COOP_AGENT", None)
            else:
                os.environ["AGENT_COOP_AGENT"] = old_agent
            if self.home is not None:
                if old_home is None:
                    os.environ.pop("AGENT_COOP_HOME", None)
                else:
                    os.environ["AGENT_COOP_HOME"] = old_home

    def msg(
        self,
        *,
        to: str,
        type: str,
        body: str,
        repo: str = "agent-harness",
        refs: str | None = None,
    ) -> int:
        if len(body) > 500:
            body = body[:497] + "..."
        argv = [
            "coop-msg",
            "--from",
            self.agent,
            "--to",
            to,
            "--type",
            type,
            "--body",
            body,
            "--repo",
            repo,
        ]
        if refs:
            argv.extend(["--refs", refs])
        if not self.available() and self.runner is _default_runner:
            return 0  # no-op when coop not installed
        cp = self._run(argv)
        return int(cp.returncode)

    def inbox_peek(self) -> str:
        if not self.available() and self.runner is _default_runner:
            return "inbox empty (coop not installed)\n"
        cp = self._run(["coop-inbox", "--peek", "--agent", self.agent])
        return (cp.stdout or "") + (cp.stderr or "")

    def inbox_drain(self) -> str:
        if not self.available() and self.runner is _default_runner:
            return "inbox empty (coop not installed)\n"
        cp = self._run(["coop-inbox", "--agent", self.agent])
        return (cp.stdout or "") + (cp.stderr or "")

    def lease_claim(self, repo: str, component: str, ttl: int = 3600) -> int:
        """Return 0 ok, 3 conflict, other error. No-op 0 if coop missing."""
        if not self.available() and self.runner is _default_runner:
            return 0
        cp = self._run(
            ["coop-lease", "claim", repo, component, str(ttl), "--agent", self.agent]
        )
        return int(cp.returncode)

    def lease_release(self, repo: str, component: str) -> int:
        if not self.available() and self.runner is _default_runner:
            return 0
        cp = self._run(
            ["coop-lease", "release", repo, component, "--agent", self.agent]
        )
        return int(cp.returncode)

    def status_text(self) -> str:
        if not self.available() and self.runner is _default_runner:
            return "coop status: (not installed)\n"
        which = shutil.which("coop")
        if not which:
            return "coop status: (coop binary missing)\n"
        cp = self._run(["coop", "status"])
        return cp.stdout or cp.stderr or ""


def parse_peek_lines(peek: str) -> list[dict[str, str]]:
    """Best-effort parse of ``coop-inbox --peek`` human output into dicts."""
    items: list[dict[str, str]] = []
    for line in peek.splitlines():
        line = line.strip()
        if not line.startswith("msg-"):
            continue
        # msg-ID [type] from->to repo
        #     body
        parts = line.split(None, 3)
        if len(parts) < 2:
            continue
        msg_id = parts[0]
        mtype = parts[1].strip("[]") if parts[1].startswith("[") else ""
        items.append({"id": msg_id, "type": mtype, "raw": line})
    return items


def load_jsonl_messages(path: str) -> list[dict[str, object]]:
    """Load a test fixture of bus-like messages (one JSON object per line)."""
    out: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out

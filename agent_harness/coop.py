"""Adapter over the `agent-coop` CLI.

agent-coop owns leases, the bus, and ff-only git sync (its ADR-0002). The harness
drives that CLI as a subprocess and reimplements none of it, so there stays exactly
one lease authority and one work queue.

Guarantees, per operation:

- ``claim``      : advisory. Returns False when another agent holds the component
                   (``coop lease claim`` exits 3). Never retries, never steals.
- ``release``    : best-effort, and only ever called for leases this process claimed.
- ``leases``     : point-in-time snapshot, parsed from human-readable output.
- ``message``    : best-effort. Bodies are truncated to the bus limit rather than
                   being rejected wholesale.
- ``inbox``      : defaults to peek. Draining is explicit and destructive.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

#: ``coop lease claim`` exits 3 when another agent already holds the component.
LEASE_HELD = 3

#: agent-coop rejects bus bodies longer than this (measured against v0.3.2).
MAX_BODY = 500

#: Message types accepted by ``coop msg --type``.
MESSAGE_TYPES = ("lease", "status", "request", "ack", "block", "handoff", "event")


@dataclass(frozen=True)
class RunResult:
    """Outcome of one subprocess invocation."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Runner(Protocol):
    """Executes an argv and returns its result. Injected so tests never fork."""

    def __call__(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> RunResult: ...


def subprocess_runner(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> RunResult:
    """Default runner: real subprocess, never raising on failure."""
    try:
        proc = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(env) if env is not None else None,
            check=False,
        )
    except FileNotFoundError:
        return RunResult(127, "", f"not found: {argv[0] if argv else '<empty>'}")
    except subprocess.TimeoutExpired:
        return RunResult(124, "", f"timeout after {timeout}s")
    return RunResult(proc.returncode, proc.stdout or "", proc.stderr or "")


@dataclass(frozen=True)
class Lease:
    """One active advisory lease as reported by ``coop lease list``."""

    agent: str
    repo: str
    component: str
    expires_epoch: int

    @property
    def key(self) -> str:
        return f"{self.repo}:{self.component}"


def parse_leases(text: str) -> list[Lease]:
    """Parse ``coop lease list`` output.

    Expected shape, whitespace-separated::

        grok     agent-harness:agent_harness/  expires_epoch=1784787681

    Unparseable lines are skipped rather than raising: a malformed line must not
    take down a supervisor loop.
    """
    leases: list[Lease] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "expires_epoch=" not in line or ":" not in line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        agent, target, expiry = parts[0], parts[1], parts[-1]
        repo, _, component = target.partition(":")
        if not repo or not component:
            continue
        try:
            expires = int(expiry.partition("=")[2])
        except ValueError:
            continue
        leases.append(
            Lease(agent=agent, repo=repo, component=component, expires_epoch=expires)
        )
    return leases


class CoopClient:
    """Thin, injectable wrapper around the ``coop`` executable."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess_runner,
        coop_bin: str = "coop",
        agent: str | None = None,
        home: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._runner = runner
        self._bin = coop_bin
        self._agent = agent or os.environ.get("AGENT_COOP_AGENT", "")
        self._home = home or os.environ.get("AGENT_COOP_HOME", "")
        self._timeout = timeout

    @property
    def agent(self) -> str:
        return self._agent

    def available(self) -> bool:
        """True when the coop executable is resolvable on PATH."""
        return shutil.which(self._bin) is not None

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self._agent:
            env["AGENT_COOP_AGENT"] = self._agent
        if self._home:
            env["AGENT_COOP_HOME"] = self._home
        # A stray per-repo env file must not silently re-point the bus.
        env.setdefault("AGENT_COOP_ENV", "/dev/null")
        return env

    def _run(self, args: Sequence[str]) -> RunResult:
        return self._runner(
            [self._bin, *args], timeout=self._timeout, env=self._env()
        )

    # -- leases ---------------------------------------------------------------

    def claim(self, repo: str, component: str, ttl: int | None = None) -> bool:
        """Claim a component. False means someone else holds it — back off.

        Exit 3 is the documented back-off signal. This method never retries and
        never escalates: retry-to-win is how two agents end up writing the same
        file.
        """
        args = ["lease", "claim", repo, component]
        if ttl is not None:
            args.append(str(ttl))
        result = self._run(args)
        if result.returncode == LEASE_HELD:
            return False
        return result.ok

    def release(self, repo: str, component: str) -> bool:
        """Release a lease. Only ever call this for a lease you claimed."""
        return self._run(["lease", "release", repo, component]).ok

    def leases(self) -> list[Lease]:
        result = self._run(["lease", "list"])
        if not result.ok:
            return []
        return parse_leases(result.stdout)

    def held_by_others(self, *, agent: str | None = None) -> set[str]:
        """Set of ``repo:component`` keys currently held by some other agent."""
        me = agent or self._agent
        return {lease.key for lease in self.leases() if lease.agent != me}

    # -- bus ------------------------------------------------------------------

    def message(
        self,
        *,
        to: str,
        type: str,
        body: str,
        repo: str | None = None,
        component: str | None = None,
        refs: Sequence[str] | None = None,
    ) -> bool:
        """Post one bus message. Over-long bodies are truncated, not dropped."""
        if type not in MESSAGE_TYPES:
            msg = f"unknown message type {type!r}; expected one of {MESSAGE_TYPES}"
            raise ValueError(msg)
        args = ["msg", "--to", to, "--type", type, "--body", clamp_body(body)]
        if repo:
            args += ["--repo", repo]
        if component:
            args += ["--component", component]
        if refs:
            args += ["--refs", " ".join(refs)]
        return self._run(args).ok

    def inbox(self, *, peek: bool = True) -> list[dict[str, Any]]:
        """Read the inbox. Peek by default — draining is destructive.

        Draining on wake is what turned 66 of grok's messages into a log entry;
        the supervisor drains only what it actually handled.
        """
        args = ["inbox", "--json"]
        if peek:
            args.append("--peek")
        result = self._run(args)
        if not result.ok:
            return []
        try:
            payload = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            messages = payload.get("messages")
            if isinstance(messages, list):
                return [item for item in messages if isinstance(item, dict)]
        return []


def clamp_body(body: str, limit: int = MAX_BODY) -> str:
    """Clamp a bus body to the agent-coop limit.

    The bus rejects over-long bodies outright, which loses the message. Losing the
    tail of a status line is strictly better than losing the whole line.
    """
    text = " ".join(body.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

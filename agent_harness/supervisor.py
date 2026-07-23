"""Autodev supervisor — short-lived sessions, durable queue via coop + local store.

Resolves agent-coop#17's hard limit: the **supervisor** is long-lived; sessions are not.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_harness.coop_bridge import CoopBridge
from agent_harness.providers import SessionResult, get_provider
from agent_harness.unit_of_work import Provider, UnitOfWork, UnitStore, new_unit


def default_home() -> Path:
    import os

    raw = os.environ.get("AGENT_HARNESS_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".local" / "state" / "agent-harness"


@dataclass
class SupervisorConfig:
    home: Path = field(default_factory=default_home)
    agent: str = "harness"
    session_timeout_s: int = 1800
    poll_s: float = 15.0
    mock_fail_times: int = 0
    claim_leases: bool = True


@dataclass
class TickReport:
    acted: bool
    unit_id: str | None
    result: str
    detail: str = ""


class Supervisor:
    """One supervisor process; many ephemeral provider sessions."""

    def __init__(self, cfg: SupervisorConfig | None = None, coop: CoopBridge | None = None) -> None:
        self.cfg = cfg or SupervisorConfig()
        self.cfg.home.mkdir(parents=True, exist_ok=True)
        self.store = UnitStore(self.cfg.home / "units")
        self.sessions_dir = self.cfg.home / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        self.coop = coop or CoopBridge(agent=self.cfg.agent)
        self._log_path = self.cfg.home / "supervisor.jsonl"

    def log(self, event: str, **fields: Any) -> None:
        rec = {"ts": time.time(), "event": event, **fields}
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def enqueue(
        self,
        *,
        title: str,
        pointer: str,
        provider: Provider = "mock",
        repo: str = "agent-harness",
        component: str = "work",
        **kwargs: Any,
    ) -> UnitOfWork:
        unit = new_unit(
            title=title,
            pointer=pointer,
            provider=provider,
            repo=repo,
            component=component,
            **kwargs,
        )
        self.store.enqueue(unit)
        self.log("enqueue", unit_id=unit.id, provider=provider, pointer=pointer)
        self.coop.msg(
            to="all",
            type="event",
            body=f"event:unit_enqueued id={unit.id} provider={provider} title={title[:80]}",
            repo="agent-harness",
            refs=unit.id,
        )
        return unit

    def board(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "queued": [u.to_dict() for u in self.store.list_state("queued")],
            "running": [u.to_dict() for u in self.store.list_state("running")],
            "done": [u.to_dict() for u in self.store.list_state("done")][-20:],
            "failed": [u.to_dict() for u in self.store.list_state("failed")][-20:],
        }

    def render_board(self) -> str:
        b = self.board()
        lines = [
            f"agent-harness supervisor  home={self.cfg.home}",
            f"  queued={len(b['queued'])} running={len(b['running'])} "
            f"done={len(b['done'])} failed={len(b['failed'])}",
            "",
        ]
        for label in ("running", "queued", "failed"):
            items = b[label]
            if not items:
                continue
            lines.append(f"## {label}")
            for u in items[:10]:
                lines.append(
                    f"  - {u['id']} [{u.get('provider')}] {u.get('title')} "
                    f"attempts={u.get('attempts')}/{u.get('max_attempts')}"
                )
            lines.append("")
        return "\n".join(lines)

    def tick(self) -> TickReport:
        """Process at most one unit. Safe for cron / ``loop --once``."""
        unit = self.store.next_queued()
        if unit is None:
            return TickReport(acted=False, unit_id=None, result="idle", detail="queue empty")

        unit.attempts += 1
        unit.state = "running"
        self.store.save(unit)
        self.log("start", unit_id=unit.id, attempt=unit.attempts, provider=unit.provider)

        if self.cfg.claim_leases:
            rc = self.coop.lease_claim(unit.repo, unit.component, unit.lease_ttl)
            if rc == 3:
                unit.state = "queued"
                unit.last_error = "lease conflict (exit 3)"
                self.store.save(unit)
                self.log("lease_conflict", unit_id=unit.id)
                return TickReport(
                    acted=True,
                    unit_id=unit.id,
                    result="backoff",
                    detail="lease exit 3 — re-queued",
                )

        work_dir = self.sessions_dir / unit.id / f"attempt-{unit.attempts}"
        provider = get_provider(unit.provider, mock_fail_times=self.cfg.mock_fail_times)
        result = provider.run(unit, work_dir=work_dir, timeout_s=self.cfg.session_timeout_s)
        return self._finish(unit, result)

    def _finish(self, unit: UnitOfWork, result: SessionResult) -> TickReport:
        if self.cfg.claim_leases:
            self.coop.lease_release(unit.repo, unit.component)

        if result.ok:
            unit.state = "done"
            unit.last_error = ""
            self.store.save(unit)
            self.log("done", unit_id=unit.id, duration_s=result.duration_s)
            self.coop.msg(
                to="all",
                type="event",
                body=(
                    f"event:unit_done id={unit.id} provider={unit.provider} "
                    f"s={result.duration_s:.1f}"
                ),
                repo=unit.repo,
                refs=unit.id,
            )
            return TickReport(acted=True, unit_id=unit.id, result="done", detail="ok")

        unit.last_error = (result.stderr or result.stdout or "fail")[:300]
        if unit.attempts >= unit.max_attempts:
            unit.state = "escalated"
            self.store.save(unit)
            self.log("escalated", unit_id=unit.id, error=unit.last_error)
            self.coop.msg(
                to="all",
                type="block",
                body=(
                    f"unit escalated id={unit.id} after {unit.attempts} fails: "
                    f"{unit.last_error[:180]}"
                ),
                repo=unit.repo,
                refs=unit.id,
            )
            return TickReport(
                acted=True,
                unit_id=unit.id,
                result="escalated",
                detail=unit.last_error,
            )

        unit.state = "queued"
        self.store.save(unit)
        self.log("retry", unit_id=unit.id, attempt=unit.attempts, error=unit.last_error)
        return TickReport(
            acted=True,
            unit_id=unit.id,
            result="retry",
            detail=unit.last_error,
        )

    def run_forever(self, *, max_ticks: int | None = None) -> int:
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            report = self.tick()
            ticks += 1
            print(
                f"tick#{ticks} acted={report.acted} result={report.result} "
                f"unit={report.unit_id or '-'} {report.detail[:80]}"
            )
            if not report.acted:
                time.sleep(self.cfg.poll_s)
            elif report.result in ("done", "escalated", "backoff", "retry"):
                # brief pause between sessions
                time.sleep(min(2.0, self.cfg.poll_s))
        return 0

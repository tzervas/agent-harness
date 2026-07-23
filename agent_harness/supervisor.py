"""The autodev supervisor loop.

This is the inversion issue #24 calls for: sessions are short-lived *on purpose*
and the loop lives in the supervisor, not inside a session. A session takes one
unit, does it, posts its result to the bus, and dies. The supervisor spawns the
next one.

The four questions #24 left open are settled here, and the answers are load-bearing:

1. **Granularity** — one ephemeral session per leased component. The lease already
   bounds the work and carries a TTL, so no extra bookkeeping is needed.
2. **Handoff** — pointer, not payload. The payload is a file under ``handoff_dir``;
   the bus message carries its path. A 500-char body cannot hold a handoff.
3. **Reaping vs TTL** — the supervisor releases only leases *it* claimed, for
   sessions it watched exit. Everything else waits for TTL expiry. Active reaping
   of another agent's lease cannot distinguish "dead" from "merely slow", so it is
   never done.
4. **Failure budget** — ``failure_budget`` consecutive failures on one unit stops
   respawning and posts a ``block`` message naming the unit. Silence is not a
   result.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from agent_harness.autoprompt import build_autoprompt, build_handoff_stub, handoff_path_for
from agent_harness.coop import CoopClient, Runner, RunResult, subprocess_runner
from agent_harness.providers import REGISTRY, Budget, NoProviderAvailable, Provider, route
from agent_harness.units import Backlog, WorkUnit

#: Outcome statuses.
OK = "ok"
FAILED = "failed"
SKIPPED_HELD = "skipped-held"
ESCALATED = "escalated"
NO_PROVIDER = "no-provider"
PLANNED = "planned"

DEFAULT_FAILURE_BUDGET = 3
DEFAULT_SESSION_TIMEOUT = 1800.0


@dataclass(frozen=True)
class SessionOutcome:
    """What happened to one unit on one pass."""

    uid: str
    status: str
    provider: str = ""
    returncode: int | None = None
    detail: str = ""
    handoff: str = ""

    @property
    def ok(self) -> bool:
        return self.status in (OK, PLANNED)

    def render(self) -> str:
        bits = [f"  [{self.status:<13}] {self.uid}"]
        if self.provider:
            bits.append(f"provider={self.provider}")
        if self.returncode is not None:
            bits.append(f"rc={self.returncode}")
        if self.detail:
            bits.append(self.detail)
        return " ".join(bits)


@dataclass
class Supervisor:
    """Long-lived supervisor over short-lived sessions."""

    coop: CoopClient
    backlog: Backlog
    handoff_dir: Path
    runner: Runner = subprocess_runner
    registry: Mapping[str, Provider] = field(default_factory=lambda: dict(REGISTRY))
    budgets: dict[str, Budget] = field(default_factory=dict)
    available: Sequence[str] | None = None
    failure_budget: int = DEFAULT_FAILURE_BUDGET
    session_timeout: float = DEFAULT_SESSION_TIMEOUT
    live: bool = False
    coop_home: str = ""
    sleeper: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        self.handoff_dir = Path(self.handoff_dir)
        if self.failure_budget < 1:
            msg = f"failure_budget must be >= 1, got {self.failure_budget}"
            raise ValueError(msg)

    # -- one unit -------------------------------------------------------------

    def execute_unit(self, unit: WorkUnit) -> SessionOutcome:
        """Run exactly one unit through one ephemeral session."""
        state = self.backlog.state_for(unit)
        if state.escalated:
            return SessionOutcome(unit.uid, ESCALATED, detail="already escalated")

        handoff = handoff_path_for(unit, self.handoff_dir)

        try:
            provider = route(
                lane=unit.lane,
                pinned=unit.provider,
                role=unit.stages[0],
                registry=self.registry,
                budgets=self.budgets,
                available=self.available,
            )
        except NoProviderAvailable as exc:
            # Dry-run is a planning surface: it must not touch the bus, must not
            # escalate, and must not fail because a provider CLI is absent from
            # this machine (CI has neither installed).
            if not self.live:
                return SessionOutcome(
                    unit.uid,
                    PLANNED,
                    detail=f"unroutable here ({exc})",
                    handoff=str(handoff),
                )
            state.escalated = True
            state.last_error = str(exc)
            self._escalate(unit, str(exc))
            return SessionOutcome(unit.uid, NO_PROVIDER, detail=str(exc))

        attempt = state.attempts + 1

        if not self.live:
            return SessionOutcome(
                unit.uid,
                PLANNED,
                provider=provider.name,
                detail=f"would claim {unit.key} and spawn {provider.name}",
                handoff=str(handoff),
            )

        if not self.coop.claim(unit.repo, unit.component, unit.ttl):
            # Exit 3. Back off — another agent is on it.
            return SessionOutcome(
                unit.uid,
                SKIPPED_HELD,
                provider=provider.name,
                detail=f"{unit.key} held by another agent",
            )

        try:
            result = None
            used: list[str] = []
            for stage in unit.stages:
                try:
                    stage_provider = route(
                        lane=unit.lane,
                        pinned=unit.provider,
                        role=stage,
                        registry=self.registry,
                        budgets=self.budgets,
                        available=self.available,
                    )
                except NoProviderAvailable:
                    stage_provider = provider
                provider = stage_provider
                used.append(f"{stage}:{stage_provider.name}")
                result = self._spawn(
                    unit,
                    stage_provider,
                    attempt=attempt,
                    prior_error=state.last_error,
                    stage=stage,
                )
                self.budgets.setdefault(stage_provider.name, Budget()).spend()
                self._ensure_handoff(unit, stage_provider, attempt, handoff)
                if not result.ok:
                    # A failed stage aborts the rest: implementing an unplanned
                    # unit, or verifying an unimplemented one, is wasted spend.
                    break

            pipeline = " -> ".join(used)
            if result is not None and result.ok:
                state.record_success(provider.name)
                self._post_result(unit, provider, handoff, ok=True, detail=pipeline)
                return SessionOutcome(
                    unit.uid,
                    OK,
                    provider=provider.name,
                    returncode=result.returncode,
                    detail=pipeline,
                    handoff=str(handoff),
                )

            assert result is not None  # unit.stages is non-empty by construction
            error = (result.stderr or result.stdout or "").strip()[:200]
            error = f"[{pipeline}] {error}" if error else f"[{pipeline}] exit {result.returncode}"
            state.record_failure(provider.name, error or f"exit {result.returncode}")
            if state.failures >= self.failure_budget:
                state.escalated = True
                self._escalate(
                    unit,
                    f"{state.failures} consecutive failures; last: {state.last_error}",
                )
                return SessionOutcome(
                    unit.uid,
                    ESCALATED,
                    provider=provider.name,
                    returncode=result.returncode,
                    detail=f"failure budget {self.failure_budget} exhausted",
                    handoff=str(handoff),
                )
            self._post_result(unit, provider, handoff, ok=False, detail=state.last_error)
            return SessionOutcome(
                unit.uid,
                FAILED,
                provider=provider.name,
                returncode=result.returncode,
                detail=state.last_error,
                handoff=str(handoff),
            )
        finally:
            # Release only what we claimed, for a session we watched exit.
            self.coop.release(unit.repo, unit.component)

    def _spawn(
        self,
        unit: WorkUnit,
        provider: Provider,
        *,
        attempt: int,
        prior_error: str,
        stage: str = "implement",
    ) -> RunResult:
        prompt = build_autoprompt(
            unit,
            handoff_dir=self.handoff_dir,
            agent_name=self.coop.agent or provider.name,
            coop_home=self.coop_home,
            attempt=attempt,
            prior_error=prior_error,
            stage=stage,
        )
        return self.runner(
            provider.build_argv(prompt),
            timeout=self.session_timeout,
        )

    def _ensure_handoff(
        self, unit: WorkUnit, provider: Provider, attempt: int, handoff: Path
    ) -> None:
        """A session that died without a handoff still leaves its successor a note."""
        handoff.parent.mkdir(parents=True, exist_ok=True)
        if not handoff.exists():
            handoff.write_text(
                build_handoff_stub(unit, provider=provider.name, attempt=attempt),
                encoding="utf-8",
            )

    # -- bus ------------------------------------------------------------------

    def _post_result(
        self,
        unit: WorkUnit,
        provider: Provider,
        handoff: Path,
        *,
        ok: bool,
        detail: str,
    ) -> None:
        verdict = "done" if ok else "FAILED"
        body = (
            f"unit {unit.uid} {verdict} via {provider.name} on {unit.key}. "
            f"handoff: {handoff}"
        )
        if detail:
            body += f" | {detail}"
        self.coop.message(
            to="all",
            type="handoff" if ok else "status",
            body=body,
            repo=unit.repo,
            component=unit.component,
            refs=[f"issue#{unit.issue}"] if unit.issue else None,
        )

    def _escalate(self, unit: WorkUnit, reason: str) -> None:
        """Stop respawning and tell a human. Silence is not a result."""
        self.coop.message(
            to="all",
            type="block",
            body=(
                f"ESCALATION: unit {unit.uid} on {unit.key} stopped after "
                f"{reason}. Supervisor will not respawn it. Human decision needed."
            ),
            repo=unit.repo,
            component=unit.component,
            refs=[f"issue#{unit.issue}"] if unit.issue else None,
        )

    # -- board ----------------------------------------------------------------

    def render_board(self) -> str:
        """Human-readable state of every unit the supervisor knows about."""
        lines = [
            f"supervisor board ({'live' if self.live else 'dry-run'})",
            f"  units: {len(self.backlog)}   failure budget: {self.failure_budget}",
            f"  handoff dir: {self.handoff_dir}",
        ]
        if not self.backlog.units:
            lines.append("  (backlog empty)")
            return "\n".join(lines)

        held = set()
        if self.live:
            held = self.coop.held_by_others()

        lines.append(
            f"  {'uid':<24} {'lane':<9} {'attempts':>8} {'fails':>6}  state"
        )
        for unit in self.backlog.units:
            st = self.backlog.state_for(unit)
            if st.escalated:
                state = "ESCALATED"
            elif unit.key in held:
                state = "held-by-other"
            elif st.failures:
                state = f"retrying ({st.last_error[:40]})"
            elif st.attempts:
                state = "done"
            else:
                state = "pending"
            lines.append(
                f"  {unit.uid:<24} {unit.lane:<9} {st.attempts:>8} {st.failures:>6}  {state}"
            )
        return "\n".join(lines)

    def board_dict(self) -> dict[str, object]:
        """Machine-readable board."""
        return {
            "live": self.live,
            "failure_budget": self.failure_budget,
            "handoff_dir": str(self.handoff_dir),
            "units": [
                {
                    "uid": unit.uid,
                    "key": unit.key,
                    "lane": unit.lane,
                    "attempts": self.backlog.state_for(unit).attempts,
                    "failures": self.backlog.state_for(unit).failures,
                    "escalated": self.backlog.state_for(unit).escalated,
                    "last_error": self.backlog.state_for(unit).last_error,
                }
                for unit in self.backlog.units
            ],
        }

    # -- the loop -------------------------------------------------------------

    def run_once(self) -> list[SessionOutcome]:
        """One pass over every unit still worth attempting."""
        pending = self.backlog.pending(failure_budget=self.failure_budget)
        return [self.execute_unit(unit) for unit in pending]

    def run(
        self,
        *,
        max_iterations: int | None = 1,
        interval: float = 0.0,
    ) -> list[list[SessionOutcome]]:
        """Drive the loop.

        ``max_iterations=None`` watches indefinitely. The loop stops early once no
        unit is worth attempting — an idle supervisor is a correct supervisor, not
        one that should invent work.
        """
        passes: list[list[SessionOutcome]] = []
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            if not self.backlog.pending(failure_budget=self.failure_budget):
                break
            passes.append(self.run_once())
            iteration += 1
            more = max_iterations is None or iteration < max_iterations
            if interval > 0 and more:
                self.sleeper(interval)
        return passes


def summarise(passes: Sequence[Sequence[SessionOutcome]]) -> dict[str, int]:
    """Count outcomes by status across every pass."""
    counts: dict[str, int] = {}
    for outcomes in passes:
        for outcome in outcomes:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
    return counts

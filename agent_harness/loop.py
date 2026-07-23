"""Ephemeral-session autoloop planner — offline, deterministic, bounded.

An **autoloop** runs a development task across repeated *ephemeral* sessions: each
iteration is a fresh session with no in-process state carried from the last one, given a
prompt derived (**autoprompt**) from the task and what previous iterations reported. It is
the automation shape behind "keep going until this is actually done" without a human
retyping the prompt each round.

Three properties are deliberate, and each exists because the obvious implementation is
unsafe:

**Bounded by construction.** ``max_iterations`` is required and hard-capped. An autoloop
whose stop condition is "when the model decides it's finished" is an unbounded spend, and
a loop that cannot make progress will happily burn the budget proving it.

**Idle-aware.** A loop that stops only at ``max_iterations`` wastes every round after the
work converges; one that stops at the first quiet round quits on a single unproductive
step. ``stop_after_idle`` requires K *consecutive* no-progress iterations, which is the
"loop until dry" shape rather than a simple counter.

**Never-silent.** Every plan enumerates its stop conditions up front and every completed
run reports which one fired. A loop that stops without saying why is indistinguishable
from a loop that crashed.

Determinism: session identifiers derive from a stable hash of task and index — no clock,
no randomness — so the same spec always yields the same plan and tests can assert on it.

Dry-run is the only supported path in v0.x, matching :mod:`agent_harness.spawn`: this
module plans an autoloop, it does not execute one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

#: Hard ceiling on iterations regardless of what a caller asks for. A planner that
#: cheerfully emits a 10_000-iteration plan is a footgun even in dry-run, because the
#: plan is what a live executor would later consume.
MAX_ITERATIONS_CAP: int = 100

#: Default consecutive-idle rounds before declaring convergence.
DEFAULT_STOP_AFTER_IDLE: int = 2

#: Stop conditions a run may report. Ordered by precedence when several could apply.
STOP_CONDITIONS: tuple[str, ...] = (
    "task-complete",  # the work reported itself done
    "converged",  # stop_after_idle consecutive no-progress iterations
    "max-iterations",  # the bound was reached
    "aborted",  # operator or executor stopped it
)


def _session_id(task: str, index: int) -> str:
    """Deterministic ephemeral-session id.

    Derived from the task and iteration index only — no clock, no randomness — so a plan
    is reproducible and testable. Sessions are *ephemeral*: the id names one throwaway
    session, and nothing is expected to survive it except what the session reports back.
    """
    digest = hashlib.sha256(f"{task}\x00{index}".encode()).hexdigest()
    return f"ah-{digest[:12]}"


def autoprompt(task: str, index: int, *, last_outcome: str | None = None) -> str:
    """Derive iteration ``index``'s prompt (the **autoprompt**).

    Iteration 0 is the task verbatim. Later iterations restate the task — an ephemeral
    session has no memory of earlier rounds, so the prompt must carry everything it needs
    — and append the previous outcome plus an explicit instruction to verify rather than
    assume prior work landed.

    That last part matters: without it a resumed session tends to trust the summary it was
    handed and re-report success it never observed.
    """
    if index < 0:
        msg = f"index must be >= 0, got {index}"
        raise ValueError(msg)
    if index == 0:
        return task
    carried = last_outcome.strip() if last_outcome and last_outcome.strip() else "(none reported)"
    return (
        f"{task}\n\n"
        f"[autoloop iteration {index}] Previous iteration reported: {carried}\n"
        "You are a fresh session and did not perform that work. Verify the current state "
        "yourself before continuing, and do not re-report prior results as your own. "
        "If the task is already complete, say so explicitly instead of finding new work."
    )


@dataclass(frozen=True)
class LoopIteration:
    """One planned ephemeral session."""

    index: int
    session_id: str
    prompt: str
    workdir_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoopPlan:
    """Local dry-run plan for an ephemeral-session autoloop."""

    task: str
    mode: str
    network: bool
    max_iterations: int
    stop_after_idle: int
    iterations: tuple[LoopIteration, ...]
    stop_conditions: tuple[str, ...] = field(default=STOP_CONDITIONS)
    isolation_hint: str = "one ephemeral session per iteration; no state carried in-process"
    validate: str = "bash scripts/local-ci.sh"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def render(self) -> str:
        stops = ", ".join(self.stop_conditions)
        lines = [
            "autoloop plan (dry-run)",
            f"  task:         {self.task}",
            f"  mode:         {self.mode}",
            f"  network:      {str(self.network).lower()}",
            f"  iterations:   {len(self.iterations)} planned (max {self.max_iterations})",
            f"  idle stop:    after {self.stop_after_idle} consecutive no-progress rounds",
            f"  stop when:    {stops}",
            f"  isolation:    {self.isolation_hint}",
            f"  validate:     {self.validate}",
            f"  note:         {self.note}",
            "  sessions:",
        ]
        lines.extend(
            f"    - [{it.index}] {it.session_id}  {it.workdir_hint}" for it in self.iterations
        )
        return "\n".join(lines)


def build_loop_plan(
    task: str,
    *,
    dry_run: bool = True,
    max_iterations: int = 5,
    stop_after_idle: int = DEFAULT_STOP_AFTER_IDLE,
) -> LoopPlan:
    """Build an ephemeral-session autoloop plan.

    Dry-run is the only supported path in v0.x: never performs network I/O and never
    starts a session. Live execution stays a hard error until a post-1.0 path is designed,
    matching :func:`agent_harness.spawn.build_spawn_plan`.
    """
    if not task.strip():
        msg = "task must be a non-empty string"
        raise ValueError(msg)
    if max_iterations < 1:
        msg = f"max_iterations must be >= 1, got {max_iterations}"
        raise ValueError(msg)
    if max_iterations > MAX_ITERATIONS_CAP:
        msg = f"max_iterations must be <= {MAX_ITERATIONS_CAP}, got {max_iterations}"
        raise ValueError(msg)
    if stop_after_idle < 1:
        msg = f"stop_after_idle must be >= 1, got {stop_after_idle}"
        raise ValueError(msg)
    if stop_after_idle > max_iterations:
        msg = (
            f"stop_after_idle ({stop_after_idle}) exceeds max_iterations "
            f"({max_iterations}); the idle stop could never fire"
        )
        raise ValueError(msg)
    if not dry_run:
        msg = "live autoloop execution is not implemented in v0.x; use --dry-run"
        raise NotImplementedError(msg)

    task = task.strip()
    iterations = tuple(
        LoopIteration(
            index=i,
            session_id=_session_id(task, i),
            prompt=autoprompt(task, i),
            workdir_hint=f"isolated worktree for {_session_id(task, i)}",
        )
        for i in range(max_iterations)
    )
    return LoopPlan(
        task=task,
        mode="dry-run",
        network=False,
        max_iterations=max_iterations,
        stop_after_idle=stop_after_idle,
        iterations=iterations,
        note=(
            "offline; plans ephemeral sessions only, starts none; each iteration is a "
            "fresh session that must verify state rather than trust the carried summary"
        ),
    )

"""Units of work for the supervisor loop.

A *unit* is the granularity decision from issue #24: **one ephemeral session per
leased component**. The lease already bounds the work and already carries a TTL, so
a unit needs no separate bookkeeping — if the session dies, the lease expires and
the unit becomes claimable again.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

#: Cost lanes, mirroring modules/agents/model-policy.md (L0-rare / L1-default).
LANES = ("build", "flagship", "fast")


@dataclass(frozen=True)
class WorkUnit:
    """One unit of work: a task scoped to exactly one leasable component."""

    uid: str
    repo: str
    component: str
    task: str
    issue: int | None = None
    lane: str = "build"
    provider: str | None = None
    validate: str = "bash scripts/local-ci.sh"
    cwd: str | None = None
    ttl: int = 3600

    def __post_init__(self) -> None:
        if not self.uid:
            msg = "uid must be non-empty"
            raise ValueError(msg)
        if not self.repo or not self.component:
            msg = f"unit {self.uid!r} needs both repo and component"
            raise ValueError(msg)
        if not self.task.strip():
            msg = f"unit {self.uid!r} needs a non-empty task"
            raise ValueError(msg)
        if self.lane not in LANES:
            msg = f"unit {self.uid!r}: lane must be one of {LANES}, got {self.lane!r}"
            raise ValueError(msg)
        if self.ttl < 1:
            msg = f"unit {self.uid!r}: ttl must be positive, got {self.ttl}"
            raise ValueError(msg)

    @property
    def key(self) -> str:
        """The ``repo:component`` lease key this unit contends for."""
        return f"{self.repo}:{self.component}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnitState:
    """Mutable per-unit bookkeeping held by the supervisor."""

    attempts: int = 0
    failures: int = 0
    escalated: bool = False
    last_error: str = ""
    last_provider: str = ""

    def record_success(self, provider: str) -> None:
        self.attempts += 1
        self.failures = 0
        self.last_error = ""
        self.last_provider = provider

    def record_failure(self, provider: str, error: str) -> None:
        self.attempts += 1
        self.failures += 1
        self.last_error = error
        self.last_provider = provider


@dataclass
class Backlog:
    """An ordered set of units plus their state."""

    units: list[WorkUnit] = field(default_factory=list)
    state: dict[str, UnitState] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.units)

    def state_for(self, unit: WorkUnit) -> UnitState:
        return self.state.setdefault(unit.uid, UnitState())

    def pending(self, *, failure_budget: int) -> list[WorkUnit]:
        """Units still worth attempting — not escalated, not over budget."""
        out: list[WorkUnit] = []
        for unit in self.units:
            st = self.state_for(unit)
            if st.escalated or st.failures >= failure_budget:
                continue
            out.append(unit)
        return out


def unit_from_dict(payload: dict[str, Any]) -> WorkUnit:
    """Build a unit from a plain dict, ignoring unknown keys."""
    known = {
        "uid",
        "repo",
        "component",
        "task",
        "issue",
        "lane",
        "provider",
        "validate",
        "cwd",
        "ttl",
    }
    return WorkUnit(**{k: v for k, v in payload.items() if k in known})


def load_units(source: str | Path) -> list[WorkUnit]:
    """Load units from a JSON file.

    Accepts either a bare list of unit objects or ``{"units": [...]}``. Offline
    only: the backlog is a local file, never a network fetch.
    """
    path = Path(source)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("units", [])
    if not isinstance(raw, list):
        msg = f"{path}: expected a list of units or {{'units': [...]}}"
        raise ValueError(msg)
    return [unit_from_dict(item) for item in raw]


def save_units(source: str | Path, units: Iterable[WorkUnit]) -> None:
    """Write units back, preserving the ``{"units": [...]}`` wrapper shape."""
    path = Path(source)
    payload = [unit.to_dict() for unit in units]
    wrapped = False
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            wrapped = isinstance(existing, dict)
        except (json.JSONDecodeError, OSError):
            wrapped = False
    body: object = {"units": payload} if wrapped else payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_unit(source: str | Path, unit: WorkUnit) -> list[WorkUnit]:
    """Append one unit to a backlog file, creating it if absent.

    Rejects a duplicate uid rather than silently shadowing it — two units with one
    uid would share per-unit state and corrupt the failure budget.
    """
    path = Path(source)
    existing = load_units(path) if path.is_file() else []
    if any(u.uid == unit.uid for u in existing):
        msg = f"backlog already contains a unit with uid {unit.uid!r}"
        raise ValueError(msg)
    updated = [*existing, unit]
    save_units(path, updated)
    return updated


def dedupe_by_key(units: Iterable[WorkUnit]) -> list[WorkUnit]:
    """Keep the first unit per lease key.

    Two units contending for one component would serialise behind the same lease
    and the loser would look like a failure. Collapse them up front instead.
    """
    seen: set[str] = set()
    out: list[WorkUnit] = []
    for unit in units:
        if unit.key in seen:
            continue
        seen.add(unit.key)
        out.append(unit)
    return out

"""Offline spawn plan builder — no network, no paid APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SpawnPlan:
    """Local dry-run plan for a swarm issue."""

    issue: int
    mode: str
    network: bool
    lane: str
    validate: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        lines = [
            "spawn plan (dry-run)",
            f"  issue:        #{self.issue}",
            f"  mode:         {self.mode}",
            f"  network:      {str(self.network).lower()}",
            f"  lane:         {self.lane}",
            f"  validate:     {self.validate}",
            f"  note:         {self.note}",
        ]
        return "\n".join(lines)


def build_spawn_plan(
    issue: int,
    *,
    dry_run: bool = True,
    lane: str = "build",
) -> SpawnPlan:
    """Build a spawn plan.

    Dry-run is the only supported path in v0: never performs network I/O.
    """
    if issue < 1:
        msg = f"issue must be a positive integer, got {issue}"
        raise ValueError(msg)
    if not dry_run:
        msg = "live spawn is not implemented in v0; use --dry-run"
        raise NotImplementedError(msg)
    return SpawnPlan(
        issue=issue,
        mode="dry-run",
        network=False,
        lane=lane,
        validate="bash scripts/local-ci.sh",
        note="offline; no GitHub fetch; fill exclusive files from issue body",
    )

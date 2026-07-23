"""Offline spawn plan builder — no network, no paid APIs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Compose-by-reference siblings (docs + doctor; not vendored).
SIBLING_REFS: dict[str, str] = {
    "cabal-devmelopner": "https://github.com/tzervas/cabal-devmelopner",
    "tg-agent-relay": "https://github.com/tzervas/tg-agent-relay",
    "agent-mcp": "https://github.com/tzervas/agent-mcp",
    "tz-forge": "https://github.com/tzervas/tz-forge",
    "gha-runner-ctl": "https://github.com/tzervas/gha-runner-ctl",
}

DEFAULT_ROLES: tuple[str, ...] = (
    "orchestrator",
    "implementer",
    "reviewer",
)

DEFAULT_EXCLUSIVE_PATHS: tuple[str, ...] = (
    # Fill from issue body exclusive-files block when present
    "src/**",
    "tests/**",
    "docs/**",
)


@dataclass(frozen=True)
class SpawnPlan:
    """Local dry-run plan for a swarm issue (E2E dry-run path)."""

    issue: int
    mode: str
    network: bool
    lane: str
    validate: str
    note: str
    roles: tuple[str, ...] = field(default=DEFAULT_ROLES)
    exclusive_paths: tuple[str, ...] = field(default=DEFAULT_EXCLUSIVE_PATHS)
    siblings: dict[str, str] = field(default_factory=lambda: dict(SIBLING_REFS))
    worktree_hint: str = "one isolated worktree per concurrent agent"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def render(self) -> str:
        roles = ", ".join(self.roles)
        paths = ", ".join(self.exclusive_paths)
        sib_lines = "\n".join(f"    - {k}: {v}" for k, v in sorted(self.siblings.items()))
        lines = [
            "spawn plan (dry-run)",
            f"  issue:        #{self.issue}",
            f"  mode:         {self.mode}",
            f"  network:      {str(self.network).lower()}",
            f"  lane:         {self.lane}",
            f"  roles:        {roles}",
            f"  exclusive:    {paths}",
            f"  worktree:     {self.worktree_hint}",
            f"  validate:     {self.validate}",
            f"  note:         {self.note}",
            "  siblings:",
            sib_lines,
        ]
        return "\n".join(lines)


def build_spawn_plan(
    issue: int,
    *,
    dry_run: bool = True,
    lane: str = "build",
    exclusive_paths: tuple[str, ...] | None = None,
    roles: tuple[str, ...] | None = None,
    live: bool = False,
    provider: str = "mock",
) -> SpawnPlan:
    """Build a spawn plan.

    Dry-run: offline plan only (default).
    Live: plan for ephemeral session via ``agent-harness loop`` / providers
    (claude -p, grok --prompt-file, or mock). Does not itself spend tokens —
    the supervisor executes the plan.
    """
    if issue < 1:
        msg = f"issue must be a positive integer, got {issue}"
        raise ValueError(msg)
    if live and dry_run:
        msg = "pass either --dry-run or --live, not both"
        raise ValueError(msg)
    if not dry_run and not live:
        # backward compatible: bare spawn without flags still errors helpfully
        msg = "live spawn requires --live (or use --dry-run for offline plan)"
        raise NotImplementedError(msg)
    if dry_run:
        return SpawnPlan(
            issue=issue,
            mode="dry-run",
            network=False,
            lane=lane,
            validate="bash scripts/local-ci.sh",
            note=(
                "offline; no GitHub fetch; fill exclusive paths from issue body; "
                "compose cabal/relay/mcp by reference only; "
                "for ephemeral autodev use: agent-harness enqueue + loop"
            ),
            roles=roles or DEFAULT_ROLES,
            exclusive_paths=exclusive_paths or DEFAULT_EXCLUSIVE_PATHS,
            siblings=dict(SIBLING_REFS),
        )
    return SpawnPlan(
        issue=issue,
        mode=f"live/{provider}",
        network=True,
        lane=lane,
        validate="coop bus handoff + local-ci if code",
        note=(
            f"ephemeral {provider} session; supervisor owns loop; "
            "unit pointer handoff; lease TTL reclaim; failure budget escalate"
        ),
        roles=roles or DEFAULT_ROLES,
        exclusive_paths=exclusive_paths or DEFAULT_EXCLUSIVE_PATHS,
        siblings={
            **dict(SIBLING_REFS),
            "agent-coop": "https://github.com/tzervas/agent-coop",
        },
    )

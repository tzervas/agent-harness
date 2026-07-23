"""Unit of work — pointer-first handoff (fleet practice, issue #24).

A session dies; the successor loads the **pointer**, not a 500-char dump of state.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Provider = Literal["claude", "grok", "mock"]
UnitState = Literal["queued", "running", "done", "failed", "escalated"]


@dataclass
class UnitOfWork:
    """One short-lived session's assignment."""

    id: str
    title: str
    pointer: str  # path or URL to full plan/handoff
    provider: Provider = "mock"
    repo: str = "agent-harness"
    component: str = "work"
    lease_ttl: int = 3600
    max_attempts: int = 3
    attempts: int = 0
    state: UnitState = "queued"
    prompt_extra: str = ""
    created_unix: float = field(default_factory=time.time)
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UnitOfWork:
        return cls(
            id=str(d["id"]),
            title=str(d.get("title") or d["id"]),
            pointer=str(d["pointer"]),
            provider=d.get("provider") or "mock",  # type: ignore[arg-type]
            repo=str(d.get("repo") or "agent-harness"),
            component=str(d.get("component") or "work"),
            lease_ttl=int(d.get("lease_ttl") or 3600),
            max_attempts=int(d.get("max_attempts") or 3),
            attempts=int(d.get("attempts") or 0),
            state=d.get("state") or "queued",  # type: ignore[arg-type]
            prompt_extra=str(d.get("prompt_extra") or ""),
            created_unix=float(d.get("created_unix") or time.time()),
            last_error=str(d.get("last_error") or ""),
        )

    def render_prompt(self) -> str:
        """Prompt injected into an ephemeral session."""
        lines = [
            f"# Unit of work `{self.id}`",
            "",
            f"**Title:** {self.title}",
            f"**Provider:** {self.provider}",
            f"**Repo / component:** {self.repo}:{self.component}",
            f"**Pointer (load this):** `{self.pointer}`",
            "",
            "You are a **short-lived** session. Do only this unit.",
            "1. Read the pointer file/path fully.",
            "2. Claim lease if needed (`coop-lease claim`); exit 3 = back off.",
            "3. Complete the unit; post results via `coop-msg` handoff/status.",
            "4. Leave a handoff pointer if unfinished — do not dump secrets.",
            "5. Exit cleanly when done (context exhaustion is expected).",
            "",
        ]
        if self.prompt_extra:
            lines.extend(["## Extra", self.prompt_extra, ""])
        return "\n".join(lines)


def new_unit(
    *,
    title: str,
    pointer: str,
    provider: Provider = "mock",
    repo: str = "agent-harness",
    component: str = "work",
    **kwargs: Any,
) -> UnitOfWork:
    return UnitOfWork(
        id=f"uow-{uuid.uuid4().hex[:12]}",
        title=title,
        pointer=pointer,
        provider=provider,
        repo=repo,
        component=component,
        **kwargs,
    )


class UnitStore:
    """Filesystem queue under ``$AGENT_HARNESS_HOME/units``."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "queued").mkdir(exist_ok=True)
        (self.root / "running").mkdir(exist_ok=True)
        (self.root / "done").mkdir(exist_ok=True)
        (self.root / "failed").mkdir(exist_ok=True)

    def _path(self, state: UnitState, unit_id: str) -> Path:
        folder = "failed" if state == "escalated" else state
        return self.root / folder / f"{unit_id}.json"

    def save(self, unit: UnitOfWork) -> Path:
        # remove from other folders
        for st in ("queued", "running", "done", "failed"):
            p = self.root / st / f"{unit.id}.json"
            if p.is_file() and st != unit.state and not (
                unit.state == "escalated" and st == "failed"
            ):
                p.unlink(missing_ok=True)
        path = self._path(unit.state, unit.id)
        path.write_text(json.dumps(unit.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def load(self, unit_id: str) -> UnitOfWork | None:
        for st in ("queued", "running", "done", "failed"):
            p = self.root / st / f"{unit_id}.json"
            if p.is_file():
                return UnitOfWork.from_dict(json.loads(p.read_text(encoding="utf-8")))
        return None

    def list_state(self, state: UnitState) -> list[UnitOfWork]:
        folder = "failed" if state == "escalated" else state
        out: list[UnitOfWork] = []
        for p in sorted((self.root / folder).glob("*.json")):
            out.append(UnitOfWork.from_dict(json.loads(p.read_text(encoding="utf-8"))))
        return out

    def next_queued(self) -> UnitOfWork | None:
        items = self.list_state("queued")
        return items[0] if items else None

    def enqueue(self, unit: UnitOfWork) -> Path:
        unit.state = "queued"
        return self.save(unit)

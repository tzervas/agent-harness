"""Offline AJL inventory loader — reads docs/inventory stub (no network)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_RECOMMENDATIONS = frozenset({"skip", "watch", "fork"})
ALLOWED_STATUSES = frozenset({"empty_shortlist", "in_progress", "complete"})


@dataclass(frozen=True)
class InventoryCandidate:
    repo: str
    role_fit: str
    score: int
    recommendation: str
    notes: str


@dataclass(frozen=True)
class AjlInventory:
    schema_version: int
    epic: int
    status: str
    rationale: str
    candidates: tuple[InventoryCandidate, ...]
    source: Path

    @property
    def shortlist_empty(self) -> bool:
        return len(self.candidates) == 0


def default_inventory_path() -> Path:
    """Resolve docs/inventory/ajl_shortlist.json from package or cwd."""
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "docs" / "inventory" / "ajl_shortlist.json"
        if candidate.is_file():
            return candidate
    cwd = Path.cwd() / "docs" / "inventory" / "ajl_shortlist.json"
    if cwd.is_file():
        return cwd
    msg = "docs/inventory/ajl_shortlist.json not found"
    raise FileNotFoundError(msg)


def load_ajl_inventory(path: Path | None = None) -> AjlInventory:
    """Load and lightly validate the Epic 1 inventory JSON stub."""
    inv_path = path or default_inventory_path()
    raw: dict[str, Any] = json.loads(inv_path.read_text(encoding="utf-8"))

    schema_version = int(raw.get("schema_version", 0))
    if schema_version != 1:
        msg = f"unsupported schema_version: {schema_version}"
        raise ValueError(msg)

    epic = int(raw.get("epic", 0))
    if epic != 1:
        msg = f"inventory epic must be 1, got {epic}"
        raise ValueError(msg)

    status = str(raw.get("status", ""))
    if status not in ALLOWED_STATUSES:
        msg = f"status must be one of {sorted(ALLOWED_STATUSES)}, got {status!r}"
        raise ValueError(msg)

    rationale = str(raw.get("rationale", "")).strip()
    if not rationale:
        msg = "rationale must be non-empty (empty shortlist still needs rationale)"
        raise ValueError(msg)

    candidates_raw = raw.get("candidates", [])
    if not isinstance(candidates_raw, list):
        msg = "candidates must be a list"
        raise ValueError(msg)

    candidates: list[InventoryCandidate] = []
    for item in candidates_raw:
        if not isinstance(item, dict):
            msg = "each candidate must be an object"
            raise ValueError(msg)
        rec = str(item.get("recommendation", "")).lower()
        if rec not in ALLOWED_RECOMMENDATIONS:
            msg = f"recommendation must be skip|watch|fork, got {rec!r}"
            raise ValueError(msg)
        score = int(item.get("score", -1))
        if score < 0 or score > 24:
            msg = f"score must be 0–24, got {score}"
            raise ValueError(msg)
        repo = str(item.get("repo", "")).strip()
        if not repo:
            msg = "candidate.repo must be non-empty"
            raise ValueError(msg)
        candidates.append(
            InventoryCandidate(
                repo=repo,
                role_fit=str(item.get("role_fit", "")),
                score=score,
                recommendation=rec,
                notes=str(item.get("notes", "")),
            )
        )

    if status == "empty_shortlist" and candidates:
        msg = "status empty_shortlist requires candidates == []"
        raise ValueError(msg)

    return AjlInventory(
        schema_version=schema_version,
        epic=epic,
        status=status,
        rationale=rationale,
        candidates=tuple(candidates),
        source=inv_path,
    )

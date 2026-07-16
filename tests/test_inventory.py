"""Offline Epic 1 inventory stub tests — no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_harness.inventory import (
    default_inventory_path,
    load_ajl_inventory,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_MD = REPO_ROOT / "docs" / "inventory" / "AJL_INVENTORY.md"
INVENTORY_JSON = REPO_ROOT / "docs" / "inventory" / "ajl_shortlist.json"


def test_inventory_docs_exist() -> None:
    assert INVENTORY_MD.is_file()
    assert INVENTORY_JSON.is_file()


def test_inventory_md_documents_empty_shortlist() -> None:
    text = INVENTORY_MD.read_text(encoding="utf-8")
    assert "Empty shortlist rationale" in text
    assert "OPEN" in text
    assert "ajl_shortlist.json" in text


def test_default_path_resolves() -> None:
    path = default_inventory_path()
    assert path.is_file()
    assert path.name == "ajl_shortlist.json"


def test_load_empty_shortlist() -> None:
    inv = load_ajl_inventory(INVENTORY_JSON)
    assert inv.schema_version == 1
    assert inv.epic == 1
    assert inv.status == "empty_shortlist"
    assert inv.shortlist_empty
    assert inv.candidates == ()
    assert len(inv.rationale) > 20


def test_json_roundtrip_keys() -> None:
    raw = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    assert raw["candidates"] == []
    assert raw["human_gate"]
    assert "AJL" in raw["rationale"] or "fork" in raw["rationale"].lower()


def test_rejects_bad_status(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "epic": 1,
                "status": "nope",
                "rationale": "x" * 30,
                "candidates": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="status"):
        load_ajl_inventory(p)


def test_rejects_empty_rationale(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "epic": 1,
                "status": "empty_shortlist",
                "rationale": "  ",
                "candidates": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="rationale"):
        load_ajl_inventory(p)

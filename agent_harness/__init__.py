"""agent-harness: thin multi-agent orchestrator package (stdlib only at runtime)."""

from __future__ import annotations

from pathlib import Path

__all__ = ["__version__", "read_version"]


def read_version() -> str:
    """Return the repo VERSION file contents, or the package fallback."""
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "VERSION"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    return "0.0.1-dev"


__version__ = read_version()

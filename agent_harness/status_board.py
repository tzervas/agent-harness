"""Human-readable supervisor board.

Plain stdlib text. A richer TUI may wrap this later — `cabal-devmelopner` already
ships a textual one, so this deliberately stays a renderer rather than growing a
second interface.
"""

from __future__ import annotations

from agent_harness.supervisor import Supervisor


def render_board(sup: Supervisor, *, include_coop: bool = True) -> str:
    """Board plus, optionally, live coop state."""
    sections = [sup.render_board()]
    if include_coop:
        if sup.coop.available():
            sections.append("--- coop ---")
            sections.append(sup.coop.status_text().rstrip())
            sections.append("--- inbox (peek, not drained) ---")
            sections.append(sup.coop.inbox_peek_text().rstrip() or "(empty)")
        else:
            sections.append("--- coop ---")
            sections.append("(coop not on PATH; board is local-only)")
    return "\n".join(sections)


def print_board(sup: Supervisor, *, include_coop: bool = True) -> None:
    print(render_board(sup, include_coop=include_coop))

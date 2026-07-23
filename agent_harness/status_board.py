"""Human-readable supervisor board (stdlib). Full TUI may wrap this later."""

from __future__ import annotations

from agent_harness.supervisor import Supervisor


def print_board(sup: Supervisor) -> None:
    print(sup.render_board())
    print("--- coop ---")
    print(sup.coop.status_text().rstrip())
    print("--- inbox peek ---")
    print(sup.coop.inbox_peek().rstrip() or "(empty)")

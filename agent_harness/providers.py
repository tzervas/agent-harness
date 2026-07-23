"""Provider registry and routing.

Two providers with different cost, context and capability profiles. The supervisor
picks one per unit of work. Routing inputs, from issue #24:

- remaining budget/usage per provider — the actual optimisation target
- task shape (lane) — a mechanical sweep does not need a design-fork tier
- capability — some work is provider-specific
- lease conflicts — if a component is held, route elsewhere rather than block

Both CLIs expose a single-shot headless mode, which is what makes an ephemeral
session possible at all:

    claude -p "<prompt>" --output-format json
    grok   -p "<prompt>" --output-format json
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    """How to invoke one provider as a one-shot, non-interactive session."""

    name: str
    binary: str
    prompt_flag: str = "-p"
    extra_args: tuple[str, ...] = ()
    lanes: frozenset[str] = field(default_factory=lambda: frozenset({"build", "fast"}))
    #: Relative preference when several providers can serve a unit (higher wins).
    weight: int = 0

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def build_argv(self, prompt: str) -> list[str]:
        """Full argv for a single-turn headless run."""
        return [self.binary, self.prompt_flag, prompt, *self.extra_args]


CLAUDE = Provider(
    name="claude",
    binary="claude",
    prompt_flag="-p",
    extra_args=("--output-format", "json"),
    lanes=frozenset({"build", "flagship", "fast"}),
    weight=10,
)

GROK = Provider(
    name="grok",
    binary="grok",
    prompt_flag="-p",
    extra_args=("--output-format", "json"),
    lanes=frozenset({"build", "fast"}),
    weight=5,
)

REGISTRY: dict[str, Provider] = {p.name: p for p in (CLAUDE, GROK)}


@dataclass
class Budget:
    """Remaining usage headroom for one provider.

    ``remaining`` is deliberately unitless — sessions, tokens or dollars, whatever
    the operator tracks. Zero or less means "do not route here".
    """

    remaining: float = float("inf")

    def spend(self, amount: float = 1.0) -> None:
        if self.remaining != float("inf"):
            self.remaining -= amount

    @property
    def exhausted(self) -> bool:
        return self.remaining <= 0


class NoProviderAvailable(RuntimeError):
    """Raised when nothing can serve a unit — an escalation, not a retry."""


def route(
    *,
    lane: str,
    pinned: str | None = None,
    registry: Mapping[str, Provider] | None = None,
    budgets: Mapping[str, Budget] | None = None,
    available: Sequence[str] | None = None,
) -> Provider:
    """Choose a provider for one unit.

    ``available`` overrides PATH detection so tests never depend on what happens to
    be installed. Raises :class:`NoProviderAvailable` rather than silently falling
    back to a provider that cannot serve the lane — a wrong-tier session is worse
    than an honest escalation.
    """
    reg = dict(registry or REGISTRY)
    budgets = budgets or {}

    def is_available(p: Provider) -> bool:
        if available is not None:
            return p.name in available
        return p.available()

    if pinned:
        provider = reg.get(pinned)
        if provider is None:
            msg = f"unknown provider {pinned!r}; known: {sorted(reg)}"
            raise NoProviderAvailable(msg)
        if not is_available(provider):
            msg = f"pinned provider {pinned!r} is not installed"
            raise NoProviderAvailable(msg)
        if budgets.get(pinned, Budget()).exhausted:
            msg = f"pinned provider {pinned!r} is out of budget"
            raise NoProviderAvailable(msg)
        return provider

    candidates = [
        p
        for p in reg.values()
        if lane in p.lanes and is_available(p) and not budgets.get(p.name, Budget()).exhausted
    ]
    if not candidates:
        msg = (
            f"no provider available for lane {lane!r} "
            f"(installed+in-budget of {sorted(reg)})"
        )
        raise NoProviderAvailable(msg)

    # Highest weight wins; ties break on the most budget headroom, then name.
    def sort_key(p: Provider) -> tuple[int, float, str]:
        remaining = budgets.get(p.name, Budget()).remaining
        # inf sorts fine as a float; negate for descending order.
        return (-p.weight, -remaining, p.name)

    return sorted(candidates, key=sort_key)[0]


def installed(registry: Mapping[str, Provider] | None = None) -> list[str]:
    """Names of providers resolvable on PATH right now."""
    reg = registry or REGISTRY
    return sorted(name for name, p in reg.items() if p.available())

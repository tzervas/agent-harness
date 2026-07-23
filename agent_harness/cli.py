"""stdlib argparse CLI — zero runtime dependencies."""

from __future__ import annotations

import argparse
import json as _json
import os
import shutil
import sys
from pathlib import Path

from agent_harness import __version__, read_version
from agent_harness.coop import CoopClient
from agent_harness.providers import Budget, installed
from agent_harness.spawn import SIBLING_REFS, build_spawn_plan
from agent_harness.supervisor import Supervisor, summarise
from agent_harness.units import Backlog, dedupe_by_key, load_units


def _cmd_version(_: argparse.Namespace) -> int:
    # Prefer live VERSION file when present (editable / repo checkout).
    print(read_version() or __version__)
    return 0


def _cmd_spawn(args: argparse.Namespace) -> int:
    dry_run = bool(args.dry_run)
    exclusive: tuple[str, ...] | None = None
    if args.exclusive:
        exclusive = tuple(p.strip() for p in args.exclusive if p.strip())
    try:
        plan = build_spawn_plan(
            args.issue,
            dry_run=dry_run,
            lane=args.lane,
            exclusive_paths=exclusive,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(plan.to_json())
    else:
        print(plan.render())
    return 0


def _sibling_roots() -> list[Path]:
    """Candidate parent dirs for compose-by-reference siblings (offline)."""
    cwd = Path.cwd().resolve()
    roots = [cwd.parent, cwd]
    env = __import__("os").environ.get("AGENT_HARNESS_SIBLING_ROOT")
    if env:
        roots.insert(0, Path(env).expanduser().resolve())
    # de-dupe preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _cmd_doctor(_: argparse.Namespace) -> int:
    """Report local environment readiness (offline checks only)."""
    checks: list[tuple[str, bool, str]] = []

    py_ok = sys.version_info >= (3, 14)
    checks.append(
        (
            "python>=3.14",
            py_ok,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    uv_path = shutil.which("uv")
    checks.append(("uv on PATH", uv_path is not None, uv_path or "missing"))

    root = Path.cwd()
    version_file = root / "VERSION"
    checks.append(
        (
            "VERSION file",
            version_file.is_file(),
            version_file.as_posix() if version_file.is_file() else "not in cwd",
        )
    )

    local_ci = root / "scripts" / "local-ci.sh"
    checks.append(
        (
            "scripts/local-ci.sh",
            local_ci.is_file(),
            local_ci.as_posix() if local_ci.is_file() else "not in cwd",
        )
    )

    print("doctor (offline)")
    failed = 0
    for name, ok, detail in checks:
        status = "ok" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{status}] {name}: {detail}")
    print(f"  version: {read_version()}")
    return 1 if failed else 0


def _cmd_compose_doctor(_: argparse.Namespace) -> int:
    """Offline compose-by-reference checks (siblings optional; never fail on missing)."""
    print("compose-doctor (offline, advisory)")
    roots = _sibling_roots()
    print(f"  search roots: {', '.join(str(r) for r in roots)}")
    found = 0
    for name, url in sorted(SIBLING_REFS.items()):
        path_hit: Path | None = None
        for root in roots:
            candidate = root / name
            if candidate.is_dir() and (
                (candidate / ".git").exists() or (candidate / "README.md").is_file()
            ):
                path_hit = candidate
                break
        if path_hit is not None:
            found += 1
            print(f"  [ok] {name}: {path_hit}  ({url})")
        else:
            print(f"  [--] {name}: not in sibling roots  ({url})")
    print(f"  siblings present: {found}/{len(SIBLING_REFS)} (advisory; compose by ref)")
    print("  note: missing siblings are OK — harness never vendors them")
    return 0


def _parse_budgets(pairs: list[str]) -> dict[str, Budget]:
    """Parse repeated ``--budget name=N`` flags."""
    budgets: dict[str, Budget] = {}
    for pair in pairs:
        name, sep, raw = pair.partition("=")
        if not sep:
            msg = f"--budget expects name=N, got {pair!r}"
            raise ValueError(msg)
        try:
            budgets[name.strip()] = Budget(remaining=float(raw))
        except ValueError as exc:
            msg = f"--budget {pair!r}: {raw!r} is not a number"
            raise ValueError(msg) from exc
    return budgets


def _cmd_loop(args: argparse.Namespace) -> int:
    """Supervise ephemeral sessions over a backlog of units."""
    try:
        units = dedupe_by_key(load_units(args.units))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except _json.JSONDecodeError as exc:
        print(f"error: {args.units}: invalid JSON: {exc}", file=sys.stderr)
        return 2

    if not units:
        print("loop: backlog is empty; nothing to do")
        return 0

    try:
        budgets = _parse_budgets(args.budget)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    coop = CoopClient(
        agent=args.agent or os.environ.get("AGENT_COOP_AGENT") or "",
        home=args.coop_home or os.environ.get("AGENT_COOP_HOME") or "",
    )
    if args.live and not coop.available():
        print(
            "error: --live needs the `coop` executable on PATH "
            "(agent-coop is a hard dependency of the loop)",
            file=sys.stderr,
        )
        return 2

    supervisor = Supervisor(
        coop=coop,
        backlog=Backlog(units=list(units)),
        handoff_dir=Path(args.handoff_dir).expanduser(),
        budgets=budgets,
        failure_budget=args.failure_budget,
        session_timeout=args.session_timeout,
        live=bool(args.live),
        coop_home=args.coop_home or os.environ.get("AGENT_COOP_HOME", ""),
    )

    mode = "live" if args.live else "dry-run"
    max_iterations = None if args.watch else args.max_iterations
    print(f"autodev loop ({mode})")
    print(f"  units:          {len(units)}")
    print(f"  providers:      {', '.join(installed()) or 'none installed'}")
    print(f"  failure budget: {args.failure_budget}")
    print(f"  handoff dir:    {args.handoff_dir}")
    print(f"  iterations:     {'watch' if max_iterations is None else max_iterations}")

    passes = supervisor.run(max_iterations=max_iterations, interval=args.interval)

    for index, outcomes in enumerate(passes, start=1):
        print(f"  -- pass {index} --")
        for outcome in outcomes:
            print(outcome.render())

    counts = summarise(passes)
    if args.json:
        print(_json.dumps(counts, indent=2, sort_keys=True))
    else:
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nothing to do"
        print(f"  summary: {summary}")

    # Escalations and hard failures are the only non-zero exits: a held lease is a
    # correct back-off, not an error.
    if counts.get("escalated") or counts.get("no-provider"):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-harness",
        description="Thin multi-agent harness CLI (offline dry-run first).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="Print package / VERSION string")
    p_version.set_defaults(func=_cmd_version)

    p_spawn = sub.add_parser(
        "spawn",
        help="Build a swarm spawn plan (use --dry-run; no network)",
    )
    p_spawn.add_argument(
        "--issue",
        type=int,
        required=True,
        help="GitHub issue number (not fetched in dry-run)",
    )
    p_spawn.add_argument(
        "--dry-run",
        action="store_true",
        help="Offline plan only (required in v0.x; no network)",
    )
    p_spawn.add_argument(
        "--lane",
        default="build",
        choices=("build", "flagship", "fast"),
        help="Cost lane (default: build)",
    )
    p_spawn.add_argument(
        "--exclusive",
        action="append",
        default=[],
        metavar="GLOB",
        help="Exclusive path glob for this leaf (repeatable); default template if omitted",
    )
    p_spawn.add_argument(
        "--json",
        action="store_true",
        help="Emit plan as JSON (machine-readable dry-run)",
    )
    p_spawn.set_defaults(func=_cmd_spawn)

    p_doctor = sub.add_parser("doctor", help="Offline environment checks")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_compose = sub.add_parser(
        "compose-doctor",
        help="Advisory offline checks for compose-by-reference siblings",
    )
    p_compose.set_defaults(func=_cmd_compose_doctor)

    p_loop = sub.add_parser(
        "loop",
        help="Supervise ephemeral sessions over a backlog (dry-run unless --live)",
        description=(
            "Autodev supervisor: one short-lived session per leased component. "
            "Dry-run by default — it claims no leases and spawns nothing."
        ),
    )
    p_loop.add_argument(
        "--units",
        required=True,
        metavar="FILE",
        help="JSON backlog: a list of units, or {'units': [...]}",
    )
    p_loop.add_argument(
        "--live",
        action="store_true",
        help="Actually claim leases and spawn sessions (default: plan only)",
    )
    p_loop.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        metavar="N",
        help="Passes over the backlog (default: 1)",
    )
    p_loop.add_argument(
        "--watch",
        action="store_true",
        help="Loop until no unit is worth attempting (overrides --max-iterations)",
    )
    p_loop.add_argument(
        "--interval",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Sleep between passes (default: 0)",
    )
    p_loop.add_argument(
        "--failure-budget",
        type=int,
        default=3,
        metavar="N",
        help="Consecutive failures per unit before escalating (default: 3)",
    )
    p_loop.add_argument(
        "--session-timeout",
        type=float,
        default=1800.0,
        metavar="SECONDS",
        help="Hard timeout for one ephemeral session (default: 1800)",
    )
    p_loop.add_argument(
        "--handoff-dir",
        default=".coop/handoff",
        metavar="DIR",
        help="Where sessions write handoff files (default: .coop/handoff)",
    )
    p_loop.add_argument(
        "--budget",
        action="append",
        default=[],
        metavar="NAME=N",
        help="Remaining budget for a provider (repeatable), e.g. claude=5",
    )
    p_loop.add_argument("--agent", default="", help="Override AGENT_COOP_AGENT")
    p_loop.add_argument("--coop-home", default="", help="Override AGENT_COOP_HOME")
    p_loop.add_argument("--json", action="store_true", help="Emit the summary as JSON")
    p_loop.set_defaults(func=_cmd_loop)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

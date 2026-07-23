"""stdlib argparse CLI — zero runtime dependencies."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from agent_harness import __version__, read_version
from agent_harness.spawn import SIBLING_REFS, build_spawn_plan
from agent_harness.status_board import print_board
from agent_harness.supervisor import Supervisor, SupervisorConfig, default_home


def _cmd_version(_: argparse.Namespace) -> int:
    print(read_version() or __version__)
    return 0


def _cmd_spawn(args: argparse.Namespace) -> int:
    dry_run = bool(args.dry_run)
    live = bool(getattr(args, "live", False))
    exclusive: tuple[str, ...] | None = None
    if args.exclusive:
        exclusive = tuple(p.strip() for p in args.exclusive if p.strip())
    try:
        plan = build_spawn_plan(
            args.issue,
            dry_run=dry_run,
            live=live,
            lane=args.lane,
            exclusive_paths=exclusive,
            provider=getattr(args, "provider", "mock"),
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
        if live:
            print(
                "\nnote: plan only — enqueue a unit and run "
                "`agent-harness loop --once` to execute."
            )
    return 0


def _sibling_roots() -> list[Path]:
    cwd = Path.cwd().resolve()
    roots = [cwd.parent, cwd]
    env = __import__("os").environ.get("AGENT_HARNESS_SIBLING_ROOT")
    if env:
        roots.insert(0, Path(env).expanduser().resolve())
    seen: set[Path] = set()
    out: list[Path] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _cmd_doctor(_: argparse.Namespace) -> int:
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

    for bin_name in ("coop-msg", "coop-inbox", "coop-lease", "claude", "grok"):
        p = shutil.which(bin_name)
        checks.append((f"{bin_name} on PATH", p is not None, p or "missing (ok if unused)"))

    print("doctor")
    failed = 0
    hard = {"python>=3.14", "uv on PATH", "VERSION file", "scripts/local-ci.sh"}
    for name, ok, detail in checks:
        status = "ok" if ok else ("FAIL" if name in hard else "warn")
        if name in hard and not ok:
            failed += 1
        print(f"  [{status}] {name}: {detail}")
    print(f"  version: {read_version()}")
    print(f"  harness home: {default_home()}")
    return 1 if failed else 0


def _cmd_compose_doctor(_: argparse.Namespace) -> int:
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


def _sup(args: argparse.Namespace) -> Supervisor:
    home = Path(args.home).expanduser() if getattr(args, "home", None) else default_home()
    return Supervisor(
        SupervisorConfig(
            home=home,
            agent=getattr(args, "agent", "harness"),
            session_timeout_s=int(getattr(args, "timeout", 1800)),
            poll_s=float(getattr(args, "poll", 15.0)),
            mock_fail_times=int(getattr(args, "mock_fail_times", 0)),
            claim_leases=not bool(getattr(args, "no_lease", False)),
        )
    )


def _cmd_enqueue(args: argparse.Namespace) -> int:
    sup = _sup(args)
    unit = sup.enqueue(
        title=args.title,
        pointer=args.pointer,
        provider=args.provider,
        repo=args.repo,
        component=args.component,
        max_attempts=args.max_attempts,
        prompt_extra=args.prompt_extra or "",
    )
    print(f"enqueued {unit.id}")
    print(f"  provider={unit.provider} pointer={unit.pointer}")
    return 0


def _cmd_loop(args: argparse.Namespace) -> int:
    sup = _sup(args)
    if args.once:
        report = sup.tick()
        print(
            f"result={report.result} acted={report.acted} "
            f"unit={report.unit_id or '-'} {report.detail}"
        )
        return 0 if report.result in ("idle", "done", "backoff", "retry") else 1
    max_ticks = args.max_ticks if args.max_ticks and args.max_ticks > 0 else None
    return sup.run_forever(max_ticks=max_ticks)


def _cmd_status(args: argparse.Namespace) -> int:
    sup = _sup(args)
    if args.json:
        import json

        print(json.dumps(sup.board(), indent=2))
    else:
        print_board(sup)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-harness",
        description="Multi-agent harness: dry-run plans + ephemeral autodev supervisor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="Print package / VERSION string")
    p_version.set_defaults(func=_cmd_version)

    p_spawn = sub.add_parser(
        "spawn",
        help="Build a swarm spawn plan (--dry-run offline, or --live plan for loop)",
    )
    p_spawn.add_argument("--issue", type=int, required=True, help="GitHub issue number")
    p_spawn.add_argument(
        "--dry-run",
        action="store_true",
        help="Offline plan only (no provider exec)",
    )
    p_spawn.add_argument(
        "--live",
        action="store_true",
        help="Emit a live ephemeral-session plan (execute via enqueue+loop)",
    )
    p_spawn.add_argument(
        "--provider",
        default="mock",
        choices=("mock", "claude", "grok"),
        help="Provider for --live plans (default: mock)",
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
        help="Exclusive path glob (repeatable)",
    )
    p_spawn.add_argument("--json", action="store_true", help="JSON plan")
    p_spawn.set_defaults(func=_cmd_spawn)

    p_doctor = sub.add_parser("doctor", help="Environment checks (incl. coop/claude/grok)")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_compose = sub.add_parser(
        "compose-doctor",
        help="Advisory offline checks for compose-by-reference siblings",
    )
    p_compose.set_defaults(func=_cmd_compose_doctor)

    def _add_home(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--home",
            default=None,
            help="AGENT_HARNESS_HOME override (default: ~/.local/state/agent-harness)",
        )
        p.add_argument(
            "--agent",
            default="harness",
            help="AGENT_COOP_AGENT for bus posts (default: harness)",
        )

    p_enq = sub.add_parser("enqueue", help="Enqueue a unit of work for the supervisor")
    _add_home(p_enq)
    p_enq.add_argument("--title", required=True, help="Short title")
    p_enq.add_argument(
        "--pointer",
        required=True,
        help="Path/URL to full handoff (pointer-first, not 500-char dump)",
    )
    p_enq.add_argument(
        "--provider",
        default="mock",
        choices=("mock", "claude", "grok"),
    )
    p_enq.add_argument("--repo", default="agent-harness")
    p_enq.add_argument("--component", default="work")
    p_enq.add_argument("--max-attempts", type=int, default=3)
    p_enq.add_argument("--prompt-extra", default="")
    p_enq.set_defaults(func=_cmd_enqueue)

    p_loop = sub.add_parser(
        "loop",
        help="Run autodev supervisor (ephemeral sessions; long-lived process)",
    )
    _add_home(p_loop)
    p_loop.add_argument(
        "--once",
        action="store_true",
        help="Process at most one unit and exit",
    )
    p_loop.add_argument(
        "--max-ticks",
        type=int,
        default=0,
        help="Stop after N ticks (0 = forever when not --once)",
    )
    p_loop.add_argument("--poll", type=float, default=15.0, help="Idle poll seconds")
    p_loop.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Per-session timeout seconds",
    )
    p_loop.add_argument(
        "--no-lease",
        action="store_true",
        help="Do not claim coop leases (offline / tests)",
    )
    p_loop.add_argument(
        "--mock-fail-times",
        type=int,
        default=0,
        help="Mock provider: fail first N attempts (tests)",
    )
    p_loop.set_defaults(func=_cmd_loop)

    p_status = sub.add_parser("status", help="Supervisor board + coop peek")
    _add_home(p_status)
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

"""stdlib argparse CLI — zero runtime dependencies."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from agent_harness import __version__, read_version
from agent_harness.spawn import build_spawn_plan


def _cmd_version(_: argparse.Namespace) -> int:
    # Prefer live VERSION file when present (editable / repo checkout).
    print(read_version() or __version__)
    return 0


def _cmd_spawn(args: argparse.Namespace) -> int:
    dry_run = bool(args.dry_run)
    try:
        plan = build_spawn_plan(args.issue, dry_run=dry_run, lane=args.lane)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(plan.render())
    return 0


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
        help="Offline plan only (required in v0; no network)",
    )
    p_spawn.add_argument(
        "--lane",
        default="build",
        choices=("build", "flagship", "fast"),
        help="Cost lane (default: build)",
    )
    p_spawn.set_defaults(func=_cmd_spawn)

    p_doctor = sub.add_parser("doctor", help="Offline environment checks")
    p_doctor.set_defaults(func=_cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

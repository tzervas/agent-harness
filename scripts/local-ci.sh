#!/usr/bin/env bash
# Offline local CI mirror for agent-harness (no network spawn).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> required docs"
for f in \
  README.md \
  LICENSE \
  AGENTS.md \
  CLAUDE.md \
  CHANGELOG.md \
  docs/VISION.md \
  docs/WORKFLOW.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/EPICS.md \
  docs/INTEGRATIONS.md \
  .cz.toml
do
  test -f "$f" || { echo "missing: $f" >&2; exit 1; }
done

echo "==> VERSION"
test -f VERSION
grep -qx '0.2.0' VERSION

echo "==> uv sync"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found on PATH" >&2
  exit 1
fi
uv sync

echo "==> ruff"
uv run ruff check .

echo "==> pytest"
uv run pytest

echo "==> CLI smoke"
uv run agent-harness version | grep -q '0.2.0'
uv run agent-harness spawn --issue 3 --dry-run
uv run agent-harness doctor

echo "==> local-ci OK"

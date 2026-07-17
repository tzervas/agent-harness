# agent-harness — Claude / coding-assistant context

## Overview

Thin offline multi-agent harness CLI under `tzervas`. Stdlib-only runtime.
Commands: `version`, `spawn --dry-run`, `doctor`. Composes relay / MCP / cabal /
tz-forge by reference (see `docs/INTEGRATIONS.md`).

**Status:** alpha 0.1.x — usable offline scaffold; epics #1–#5 remain OPEN until
formal ship close on `main`.

## Project map

```
agent_harness/     # Package (stdlib only)
  cli.py           # argparse: version / spawn / doctor
  spawn.py         # Offline spawn plan builder
  inventory.py     # AJL shortlist JSON loader
tests/             # Offline pytest
scripts/
  local-ci.sh      # Preferred local gate
docs/              # Vision, workflow, architecture, integrations
AGENTS.md          # Agent rules (PR tiers, safety)
```

## Development commands

```bash
# Preferred local gate
bash scripts/local-ci.sh

# Install / sync
uv sync

# Lint
uv run ruff check .

# Tests
uv run pytest -q

# CLI smoke
uv run agent-harness version
uv run agent-harness spawn --issue 3 --dry-run
uv run agent-harness doctor

# Module entry
uv run python -m agent_harness version
```

### Optional pre-commit

```bash
# once per clone (requires pre-commit on PATH)
pre-commit install
pre-commit run --all-files
```

## Coding standards

- Python ≥ 3.14; zero runtime dependencies
- Ruff for lint (line-length 100, target py314)
- Prefer small, reviewable diffs
- No secrets in commits or logs
- Run `bash scripts/local-ci.sh` before claiming work complete
- Do **not** enable automatic Copilot code review on PRs
- Live `spawn` (without `--dry-run`) is intentionally not implemented in v0

## PR hygiene

- Feature branch → `dev` when integrating (use **`Refs #n`** only)
- Delivery / promote → `main` (use **`Closes #n`** / **`Fixes #n`**)
- See `AGENTS.md` for fuller agent rules and fleet close/reopen workflows

## Versioning

| File | Field |
|------|-------|
| `VERSION` | Canonical semver string |
| `pyproject.toml` | `[project].version` (PEP 440) |
| `.cz.toml` | Commitizen (optional) |

Bump all three together. Tag format: `v$version` (see `.cz.toml`).

## Further reading

- [README.md](README.md)
- [AGENTS.md](AGENTS.md)
- [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)
- [docs/WORKFLOW.md](docs/WORKFLOW.md)
- [docs/FLEET_STANDARDS.md](docs/FLEET_STANDARDS.md)
- [CHANGELOG.md](CHANGELOG.md)

# AGENTS.md — agent-harness (fractal-lite)

House rules for AI coding assistants (and multi-agent L0/L1 waves) working in this repo.

## Product

**agent-harness** is a thin offline multi-agent orchestrator CLI: spawn dry-run plans,
doctor environment checks, and multi-agent orchestration stubs. It composes sibling products
([tg-agent-relay](https://github.com/tzervas/tg-agent-relay),
[agent-mcp](https://github.com/tzervas/agent-mcp),
[cabal-devmelopner](https://github.com/tzervas/cabal-devmelopner),
[tz-forge](https://github.com/tzervas/tz-forge)) by reference — it does not re-home their runtimes.

## Local checks

Run before considering work complete:

```bash
bash scripts/local-ci.sh
```

That gate covers required docs, `uv sync`, ruff, pytest, and CLI smoke
(`version` / `spawn --dry-run` / `doctor` / `compose-doctor`).

Quick path:

```bash
uv sync
uv run ruff check .
uv run pytest -q
uv run agent-harness version
uv run agent-harness compose-doctor
```

## PR tiers — Refs vs Closes

| Target branch | Issue keywords | Effect |
|---------------|----------------|--------|
| Feature → `dev` (or feature base) | **`Refs #n`**, `Related to #n` | Issues stay open |
| Delivery → **`main`** | **`Closes #n`**, **`Fixes #n`** | Issues close on merge |
| Epic | `Closes #<epic>` only on full main delivery | Partial work uses Refs |

Fleet workflows:

- `close-issues-on-main.yml` — closes linked issues when PR lands on **main**
- `reopen-issues-closed-off-main.yml` — reopens if `Closes` was used off-main

Do **not** request automatic Copilot code review on PRs.

## Branch / worktree guards

- Never commit directly to `main` (PR only)
- Feature / chore / fix branches from the correct base (`dev` for integration work; `main` for fleet/docs promote when intentional)
- Prefer one worktree per concurrent wave
- Append-only for living status sections in docs / this file

## Safety

- **No secrets**, tokens, credentials, or private keys in commits, CI logs, issue/PR bodies, or spawn plans
- Offline first: `spawn` requires `--dry-run` in v0; never hit paid APIs in CI
- Do not enable `USE_SELF_HOSTED` without maintainer approval
- Honesty gate: never silent on tool/MCP failure — surface errors explicitly
- Prefer small, reviewable diffs

## Compose-by-reference

| Sibling | Role |
|---------|------|
| [tz-forge](https://github.com/tzervas/tz-forge) | Templates, fleet pack, `tz-new` project kinds |
| [tg-agent-relay](https://github.com/tzervas/tg-agent-relay) | Telegram / providers / MCP facade |
| [agent-mcp](https://github.com/tzervas/agent-mcp) | Multi-agent orchestration MCP |
| [cabal-devmelopner](https://github.com/tzervas/cabal-devmelopner) | Operator CLI/TUI; L0/L1 waves |

Details: [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

## Model policy (L0 / L1)

| Role | Use for |
|------|---------|
| **L0** | Hard architecture, naming, design forks (rare) |
| **L1** | Default implementer — code, docs, tests, PRs |

## Further reading

- [README.md](README.md) — product statement + 5-minute path
- [CLAUDE.md](CLAUDE.md) — commands map
- [docs/WORKFLOW.md](docs/WORKFLOW.md) — branches, spawn, cost lanes
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — package map
- [docs/FLEET_STANDARDS.md](docs/FLEET_STANDARDS.md) — fleet CI / issue close
- [docs/EPICS.md](docs/EPICS.md) — board honesty

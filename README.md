# agent-harness

<!-- FLEET-BADGES:BEGIN -->
[![CI](https://github.com/tzervas/agent-harness/actions/workflows/fleet-ci.yml/badge.svg?branch=main)](https://github.com/tzervas/agent-harness/actions/workflows/fleet-ci.yml?query=branch%3Amain)
[![Security](https://github.com/tzervas/agent-harness/actions/workflows/fleet-security.yml/badge.svg?branch=main)](https://github.com/tzervas/agent-harness/actions/workflows/fleet-security.yml?query=branch%3Amain)
<!-- FLEET-BADGES:END -->

## Product

**agent-harness** is a thin, offline-first multi-agent orchestrator for the
`tzervas` fleet. Use it when you need a **local dry-run spawn plan**, environment
runtime.

It is a **separate product** from [tg-agent-relay](https://github.com/tzervas/tg-agent-relay)
(phone ↔ agent surface). Harness **composes** relay, [agent-mcp](https://github.com/tzervas/agent-mcp),
[cabal-devmelopner](https://github.com/tzervas/cabal-devmelopner), and templates from
**[tz-forge](https://github.com/tzervas/tz-forge)** by reference — it does not re-home them.

MIT · Python ≥ 3.14 · **zero runtime dependencies** · optional shared CI via
[gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).

## Status

**Alpha v0.2.0** — usable offline CLI + docs pack. Not a full swarm platform yet.

| Surface | Ready? |
|---|---|
| `version` / `spawn --dry-run` / `doctor` | Yes (offline) |
| `scripts/local-ci.sh` | Yes |
| AGENTS.md + CLAUDE.md | Yes |
| Live spawn / network GitHub fetch | No (v0 intentionally) |
| Epics [#1](https://github.com/tzervas/agent-harness/issues/1)–[#5](https://github.com/tzervas/agent-harness/issues/5) | **OPEN** (board honesty) |

| Epic | Code / docs progress | Board |
|---|---|---|
| #3 Thin CLI / package | v0 scaffold landed | OPEN until formal ship close |
| #4 Relay + agent-mcp by ref | Integration notes only | OPEN |
| #5 E2E swarm dry-run | Dry-run spawn path only; full E2E later | OPEN |

## 5-minute path (offline)

Requires: [uv](https://docs.astral.sh/uv/), Python ≥ 3.14, bash. **No network APIs**
after install (lockfile resolve may fetch packages once).

```bash
git clone https://github.com/tzervas/agent-harness.git
cd agent-harness
uv sync
uv run agent-harness version
# → 0.2.0

uv run agent-harness spawn --issue 3 --dry-run
# → spawn plan (dry-run)
#      issue:        #3
#      mode:         dry-run
#      network:      false
#      lane:         build
#      validate:     bash scripts/local-ci.sh
#      note:         offline; no GitHub fetch; …

uv run agent-harness doctor
# → doctor (offline)
#      [ok] python>=3.14: …
#      [ok] uv on PATH: …
#      [ok] VERSION file: …
#      [ok] scripts/local-ci.sh: …
#      version: 0.2.0

bash scripts/local-ci.sh
# → ==> local-ci OK
```

Zero runtime dependencies (stdlib `argparse` only). Dry-run spawn never hits the network.

## Compose graph

| Dependency / reference | Role |
|---|---|
| [tzervas/tz-forge](https://github.com/tzervas/tz-forge) | Templates, fleet pack, `tz-new`, agent profiles |
| [tzervas/tg-agent-relay](https://github.com/tzervas/tg-agent-relay) | Telegram bridge, providers, MCP facade (consume, don’t fork product) |
| [tzervas/agent-mcp](https://github.com/tzervas/agent-mcp) | Multi-agent orchestration MCP (evaluate / integrate) |
| [tzervas/cabal-devmelopner](https://github.com/tzervas/cabal-devmelopner) | Operator CLI/TUI for L0/L1 waves |

Full details: [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

## Branch model

| Branch | Role |
|---|---|
| `main` | Stable; **PR only** |
| `dev` | Persistent integration |
| `feat/*` | Off `dev` (or intentional fleet branches off main) |

Issue close policy: merges to **`dev` leave issues open** (`Refs #n`); close on **`main`** only (`Closes` / `Fixes`).
See [docs/WORKFLOW.md](docs/WORKFLOW.md) and [AGENTS.md](AGENTS.md).

## Self-hosted CI

One shared runner host (not one per repo):

```yaml
runs-on: [self-hosted, linux, x64, podman]
```

Register the host with an **org** runner when possible so many repos share it.
See [gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).
Do **not** enable `USE_SELF_HOSTED` without maintainer approval.

## Docs

- [AGENTS.md](AGENTS.md) — agent rules (PR tiers, safety, compose)
- [CLAUDE.md](CLAUDE.md) — commands map for coding assistants
- [CHANGELOG.md](CHANGELOG.md) — release notes
- [docs/VISION.md](docs/VISION.md) — goals and non-goals
- [docs/WORKFLOW.md](docs/WORKFLOW.md) — orchestrator + swarms, cost lanes, spawn template
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers, package map, compose-by-reference
- [docs/DECISIONS.md](docs/DECISIONS.md) — design decisions (D1–D5)
- [docs/EPICS.md](docs/EPICS.md) — Wave C epic board links (status honesty)
- [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) — tz-forge + relay + agent-mcp + cabal
- [docs/FLEET_STANDARDS.md](docs/FLEET_STANDARDS.md) — fleet CI / issue close

## License

MIT — see [LICENSE](LICENSE).

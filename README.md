# agent-harness

**Universal multi-agent harness** (orchestrator + swarms) under `tzervas`.

MIT · Python 3.14 preferred · optional Rust later · shared CI via
[gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).

## What this is

A **separate** product from [tg-agent-relay](https://github.com/tzervas/tg-agent-relay).
The relay stays the Telegram/provider/MCP runtime; this repo composes:

| Dependency / reference | Role |
|---|---|
| `tzervas/tg-agent-relay` | Telegram bridge, providers, MCP facade (consume, don’t fork product) |
| `tzervas/agent-mcp` | Multi-agent orchestration MCP (evaluate / integrate) |
| `tzervas/*` tooling | Prefer existing monorepos over rewrites |
| Average Joe’s Labs (AJL) | **Evaluate → fork to `tzervas` → extend → PR upstream** (member access; never push AJL as write base). See [docs/AJL.md](docs/AJL.md). |

## Status

**Scaffold (v0.0.1-dev).** Thin offline CLI (`version` / `spawn --dry-run` / `doctor`)
and docs pack are implemented on `main`/`dev`.

**Board honesty (Wave C):** Epics [#1](https://github.com/tzervas/agent-harness/issues/1)–[#5](https://github.com/tzervas/agent-harness/issues/5)
remain **OPEN**. Merges to `dev` do not close them; close only via ship / promote to
`main` ([docs/WORKFLOW.md](docs/WORKFLOW.md)).

| Epic | Code / docs progress | Board |
|---|---|---|
| #1 AJL inventory | Stub + empty shortlist documented (`docs/inventory/`) | OPEN |
| #2 AJL forks | Not started (human gate) | OPEN |
| #3 Thin CLI / package | v0 scaffold landed | OPEN until formal ship close |
| #4 Relay + agent-mcp by ref | Integration notes only | OPEN |
| #5 E2E swarm dry-run | Dry-run spawn path only; full E2E later | OPEN |

Implementation continues as `swarm-ready` issues with exclusive file ownership.

## Quick start (CLI)

```bash
uv sync
uv run agent-harness version
uv run agent-harness spawn --issue 3 --dry-run
uv run agent-harness doctor
bash scripts/local-ci.sh
```

Zero runtime dependencies (stdlib `argparse` only). Dry-run spawn never hits the network.

## Branch model

| Branch | Role |
|---|---|
| `main` | Stable; **PR only** |
| `dev` | Persistent integration |
| `feat/*` | Off `dev` |

Issue close policy: merges to **`dev` leave issues open**; close on **`main`** only.
See [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Self-hosted CI

One shared runner host (not one per repo):

```yaml
runs-on: [self-hosted, linux, x64, podman]
```

Register the host with an **org** runner when possible so many repos share it.
See [gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).
Do **not** enable `USE_SELF_HOSTED` without maintainer approval.

## Docs

- [docs/VISION.md](docs/VISION.md) — goals and non-goals  
- [docs/WORKFLOW.md](docs/WORKFLOW.md) — orchestrator + swarms, cost lanes, spawn template  
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers, package map, compose-by-reference  
- [docs/AJL.md](docs/AJL.md) — AJL evaluate → fork → PR path  
- [docs/DECISIONS.md](docs/DECISIONS.md) — design decisions (D1–D5)  
- [docs/EPICS.md](docs/EPICS.md) — Wave C epic board links (status honesty)  
- [docs/inventory/AJL_INVENTORY.md](docs/inventory/AJL_INVENTORY.md) — Epic 1 shortlist stub  
- [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) — relay + agent-mcp by reference  

## License

MIT — see [LICENSE](LICENSE).

# Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  agent-harness (this repo)                              │
│  - issue / epic board conventions                       │
│  - orchestrator prompts + spawn templates               │
│  - thin CLI (agent-harness) for local dry-run swarms    │
│  - package agent_harness/ (stdlib, zero runtime deps)   │
└───────────────┬─────────────────────┬───────────────────┘
                │ compose-by-reference │
                ▼                     ▼
     tg-agent-relay              agent-mcp / other MCPs
     (Telegram, providers,       (multi-agent tools)
      MCP server stub)
```

## Package map (`agent_harness/`)

| Path | Responsibility |
|---|---|
| `agent_harness/__init__.py` | Package version export |
| `agent_harness/__main__.py` | `python -m agent_harness` entry |
| `agent_harness/cli.py` | argparse CLI: `version`, `spawn`, `doctor` |
| `agent_harness/spawn.py` | Offline spawn plan builder (no network) |
| `agent_harness/inventory.py` | Offline loader for Epic 1 AJL shortlist JSON |
| `docs/inventory/` | AJL inventory stub (markdown + `ajl_shortlist.json`) |
| `tests/` | Offline unit tests |

**Runtime dependencies:** none (Python stdlib only). Dev tools: `ruff`, `pytest` via uv.

## Compose-by-reference

- **Do not** vendor a second copy of relay or agent-mcp internals.  
- Depend on released interfaces (`docs/AGENT_INTERFACES.md` in the relay repo, MCP tools, providers).  
- Document joins in [INTEGRATIONS.md](INTEGRATIONS.md).  
- Optional future adapters stay thin and issue-owned.

## Join rules

- **Orchestrator-owned**: protocols, epic board, merge order, join contracts.  
- **Swarm-owned**: one issue, exclusive write set, offline tests.  
- **CI**: shared self-hosted labels optional (`USE_SELF_HOSTED` human gate); default `ubuntu-latest`.

## Layers

| Layer | Responsibility |
|---|---|
| Board | Epics, swarm-ready children, exclusive files |
| Control plane | Orchestrator session (rare flagship) |
| Implementers | Grok Build / cheaper models |
| Runtime adapters | Relay notify, MCP (by reference) |
| CLI | Local dry-run spawn / doctor / version |
| CI | Docs check + Python job; pinned action digests |

## Decisions

Record implemented choices in [DECISIONS.md](DECISIONS.md) (context, decision, why,
alternatives rejected) — same bar as the relay.

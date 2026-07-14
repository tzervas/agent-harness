# Architecture (draft)

```text
┌─────────────────────────────────────────────────────────┐
│  agent-harness (this repo)                              │
│  - issue / epic board conventions                       │
│  - orchestrator prompts + spawn templates               │
│  - optional thin CLI to drive local swarms              │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
                ▼                     ▼
     tg-agent-relay              agent-mcp / other MCPs
     (Telegram, providers,       (multi-agent tools)
      MCP server stub)
```

## Join rules

- **Do not** vendor a second copy of relay internals. Depend on released interfaces
  (`docs/AGENT_INTERFACES.md` in the relay repo, MCP tools, providers).
- **Orchestrator-owned**: protocols, epic board, merge order, join contracts.
- **Swarm-owned**: one issue, exclusive write set, offline tests.

## Layers (planned)

| Layer | Responsibility |
|---|---|
| Board | Epics, swarm-ready children, exclusive files |
| Control plane | Orchestrator session (rare flagship) |
| Implementers | Grok Build / cheaper models |
| Runtime adapters | Relay notify, MCP, optional ADK |
| CI | Shared self-hosted runner labels |

## Decisions

Record implemented choices in `docs/DECISIONS.md` (context, decision, why,
alternatives rejected) — same bar as the relay.

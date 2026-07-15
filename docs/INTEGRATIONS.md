# Integrations (compose by reference)

`agent-harness` orchestrates. It does **not** re-home product runtimes.

| Reference | Role | How we compose |
|---|---|---|
| [tzervas/tg-agent-relay](https://github.com/tzervas/tg-agent-relay) | Telegram bridge, providers, MCP facade | Depend on released interfaces / docs; **do not fork product into this repo** |
| [tzervas/agent-mcp](https://github.com/tzervas/agent-mcp) | Multi-agent orchestration MCP | Evaluate tools; thin adapters later; **no deep in-tree reimplementation** |
| [tzervas/gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl) | Shared self-hosted runner control | Docs + optional `runs-on` labels; **do not re-vendor** |
| Average Joe’s Labs | Candidate building blocks | Evaluate → fork under `tzervas` → PR upstream ([AJL.md](AJL.md)) |

## tg-agent-relay

**Boundary.** Relay remains the phone ↔ agent product surface.

**In scope for harness**

- Notify / status hooks via documented interfaces (see relay `docs/AGENT_INTERFACES.md` when present)
- MCP tool surface as a **consumer**
- Shared process: swarm-ready issues, exclusive files, cost lanes

**Out of scope**

- Vendoring a second copy of relay internals
- Shipping Telegram runtime inside `agent-harness`
- Coupling harness releases to every relay version bump without need

## agent-mcp

**Boundary.** Multi-agent MCP tools stay in `agent-mcp` (or its successors).

**In scope for harness**

- Document which MCP tools matter for spawn / join / status
- Optional thin client wrappers under `agent_harness/` **after** Epic 3 package exists
- Offline mocks in harness tests (no paid network in CI)

**Out of scope**

- Deep feature work that belongs in `agent-mcp`
- Embedding a full MCP server product in this repo for v0

## Compose-by-reference rules

1. Prefer **docs links, package dependencies, and MCP endpoints** over copy-paste.  
2. Any adapter code in this repo must have **exclusive write ownership** on swarm issues.  
3. Integration decisions go in [DECISIONS.md](DECISIONS.md).  
4. Architecture package map: [ARCHITECTURE.md](ARCHITECTURE.md).  
5. Human gates: no `USE_SELF_HOSTED` enablement and no AJL real-fork without approval.

## Related epics

- [#3](https://github.com/tzervas/agent-harness/issues/3) Thin CLI / package  
- [#4](https://github.com/tzervas/agent-harness/issues/4) Integrate relay + agent-mcp by reference  
- [#5](https://github.com/tzervas/agent-harness/issues/5) E2E swarm dry-run  

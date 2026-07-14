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
| Average Joe’s Labs (AJL) | **Read / evaluate only** — fork to `tzervas` if useful; never push as write base |

## Status

**Scaffold.** Design and board live in `docs/`. Implementation lands as
`swarm-ready` issues with exclusive file ownership (same process as the relay).

## Branch model

| Branch | Role |
|---|---|
| `main` | Stable; **PR only** |
| `dev` | Persistent integration |
| `feat/*` | Off `dev` |

## Self-hosted CI

One shared runner host (not one per repo):

```yaml
runs-on: [self-hosted, linux, x64, podman]
```

Register the host with an **org** runner when possible so many repos share it.
See [gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).

## Docs

- [docs/VISION.md](docs/VISION.md) — goals and non-goals  
- [docs/WORKFLOW.md](docs/WORKFLOW.md) — orchestrator + swarms, cost lanes  
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers and joins  

## License

MIT — see [LICENSE](LICENSE).

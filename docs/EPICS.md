# Epics (Wave C)

Board lives on GitHub Issues. **Merges to `dev` leave issues open.** Issues and
epics close only when work reaches **`main`** (see [WORKFLOW.md](WORKFLOW.md)).

| # | Epic | Labels | Depends on |
|---|---|---|---|
| [#1](https://github.com/tzervas/agent-harness/issues/1) | AJL inventory and fitness shortlist | `epic` | — |
| [#2](https://github.com/tzervas/agent-harness/issues/2) | Fork selected AJL components under tzervas | `epic` | #1 |
| [#3](https://github.com/tzervas/agent-harness/issues/3) | Thin CLI and package scaffold | `epic` `cli` | — |
| [#4](https://github.com/tzervas/agent-harness/issues/4) | Integrate tg-agent-relay and agent-mcp by reference | `epic` `docs` | #3 |
| [#5](https://github.com/tzervas/agent-harness/issues/5) | E2E swarm dry-run path | `epic` | #3, #4 |

## Wave intent

1. **Inventory** AJL candidates (empty shortlist OK if documented).  
2. **Fork** only with human approval → develop on `tzervas` → PR upstream.  
3. **Thin package / CLI** for offline spawn scaffolding.  
4. **Compose** relay + agent-mcp by reference (no product forks).  
5. **E2E dry-run** from swarm-ready issue → spawn template → offline checks.

## Human gates (this wave)

- Do **not** enable `USE_SELF_HOSTED` without further human approval.  
- Do **not** real-fork AJL without further human approval (Epic 1 may stop at inventory).  
- No AJL push as write base; no re-vendor of `gha-runner-ctl`; no PyPI release in v0.

## Epic close reminder

- Task issues: close when work reaches **`main`** (`Fixes #N` on promote PR).  
- Epics: close via a final ship issue with `Closes #<epic>` on **`main`**.  
- **`dev` merges leave issues open.**

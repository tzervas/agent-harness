# Integrations (compose by reference)

`agent-harness` orchestrates. It does **not** re-home product runtimes.

Compose via docs links, package dependencies, and MCP endpoints — not copy-paste
or vendored binaries. Project scaffolding and fleet standards come from
**[tz-forge](https://github.com/tzervas/tz-forge)**.

| Reference | Role | How we compose |
|---|---|---|
| [tzervas/tz-forge](https://github.com/tzervas/tz-forge) | Meta templates, fleet pack, `tz-new`, agent profiles | Source of AGENTS/CLAUDE lite templates, pre-commit, fleet workflows; use `tz-new agent-swarm` for new harness-like repos |
| [tzervas/tg-agent-relay](https://github.com/tzervas/tg-agent-relay) | Telegram bridge, providers, MCP facade | Depend on released interfaces / docs; **do not fork product into this repo** |
| [tzervas/agent-mcp](https://github.com/tzervas/agent-mcp) | Multi-agent orchestration MCP | Evaluate tools; thin adapters later; **no deep in-tree reimplementation** |
| [tzervas/cabal-devmelopner](https://github.com/tzervas/cabal-devmelopner) | Operator CLI/TUI; L0/L1 waves | Spawn / join orchestration consumers; cabal may drive harness dry-runs |
| [tzervas/gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl) | Shared self-hosted runner control | Docs + optional `runs-on` labels; **do not re-vendor** |

## tz-forge

**Boundary.** [tz-forge](https://github.com/tzervas/tz-forge) is the **template and fleet meta**
repo — not a runtime dependency of the harness CLI.

**In scope for harness**

- Align AGENTS.md / CLAUDE.md / pre-commit / fleet workflows with tz-forge modules
  (`modules/agents/*`, `modules/fleet/*`, `modules/pre-commit/*`, `modules/local-ci/*`)
- Use `project-kinds/agent-swarm` as the canonical skeleton for new swarm products
- Link catalog entries when documenting compose graphs

**Out of scope**

- Vendoring the full tz-forge tree into this repo
- Making `agent-harness` a hard runtime dependency of `tz-new` (compose is optional)

**Example**

```bash
# Scaffold a new agent-swarm project from tz-forge (sibling checkout)
uv run --project ../tz-forge tz-new agent-swarm /tmp/my-swarm --assistant=fractal-swarm
```

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
- Optional thin client wrappers under `agent_harness/` **after** package stabilizes
- Offline mocks in harness tests (no paid network in CI)

**Out of scope**

- Deep feature work that belongs in `agent-mcp`
- Embedding a full MCP server product in this repo for v0

## cabal-devmelopner

**Boundary.** Cabal is the operator-facing agent CLI/TUI for L0/L1 waves.
**Role split for joint 1.0 work:** **agent-harness orchestrates** (spawn plans,
join contracts, offline gates); **cabal-devmelopner is the leaf coding agent**
(implementer CLI/TUI). Do not invert that boundary.

**Joint execution plan (cabal 1.0):** see cabal’s
[`docs/V1_0_0_JOINT_EXECUTION.md`](https://github.com/tzervas/cabal-devmelopner/blob/dev/docs/V1_0_0_JOINT_EXECUTION.md)
(until on `dev`/`main`, use [PR #28](https://github.com/tzervas/cabal-devmelopner/pull/28)
/`feat/v1-gap-analysis`). Lane ownership, file exclusivity, and Grok/Claude
hand-offs live there — harness only points; cabal owns the plan content.

**In scope for harness**

- Document how cabal can invoke harness dry-run as a local gate step
- Share swarm-ready issue conventions and exclusive-file ownership
- Point operators at cabal for interactive multi-repo work; harness stays offline-first

**Out of scope**

- Embedding cabal’s TUI or model-routing stack in this repo
- Requiring cabal (or API keys) for `scripts/local-ci.sh` or unit tests
- Owning cabal’s v1 gap/joint-execution docs (compose pointer only)

**Example**

```bash
# From a cabal-capable workspace (optional; not required for harness CI)
uv run agent-harness spawn --issue 3 --dry-run
# cabal may wrap the same dry-run in a larger wave prompt
```

## Compose-by-reference rules

1. Prefer **docs links, package dependencies, and MCP endpoints** over copy-paste.
2. Any adapter code in this repo must have **exclusive write ownership** on swarm issues.
3. Integration decisions go in [DECISIONS.md](DECISIONS.md).
4. Architecture package map: [ARCHITECTURE.md](ARCHITECTURE.md).
6. Scaffold new swarm products from **tz-forge**, then specialize — do not fork harness solely for templates.

## Related epics

- [#3](https://github.com/tzervas/agent-harness/issues/3) Thin CLI / package
- [#4](https://github.com/tzervas/agent-harness/issues/4) Integrate relay + agent-mcp by reference
- [#5](https://github.com/tzervas/agent-harness/issues/5) E2E swarm dry-run

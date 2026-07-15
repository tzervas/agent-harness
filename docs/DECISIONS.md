# Design decisions

## How to write a decision

| Field | Content |
|---|---|
| Context | Problem / constraint |
| Decision | What we shipped |
| Why | Reasons that mattered |
| Alternatives | What else was considered |
| Why not | Why each lost |
| Where | Code / docs surfaces |

## D1 — Separate repo from tg-agent-relay

**Context.** A universal harness is not Telegram-specific; shipping it inside
the relay couples release cadence and confuses product boundaries.

**Decision.** `tzervas/agent-harness` is its own MIT repo. Relay is a dependency
/ integration target.

**Why.** Clear ownership, independent versioning, swarms can work without
touching phone runtime.

**Alternatives rejected**

| Alternative | Why not |
|---|---|
| Monorepo under relay | Forces relay version bumps for harness-only work |
| Push directly to AJL | Membership ≠ write base; always fork → PR upstream |
| Reimplement AJL capabilities in-tree | Prefer fork/extend when AJL already solves it |

**Where.** This repository; [docs/AJL.md](AJL.md); relay docs point outward for harness work.

## D2 — Prefer extending AJL via fork + upstream PR

**Context.** Useful harness/orchestration building blocks may already exist in AJL
orgs the maintainer belongs to.

**Decision.** Default path is evaluate AJL → fork under `tzervas` → develop →
PR back to AJL. `agent-harness` orchestrates; it does not replace every dependency.

**Why.** Less rewrite, better OSS hygiene, keeps personal product namespaces clean.

**Where.** [docs/AJL.md](AJL.md), Epic [#1](https://github.com/tzervas/agent-harness/issues/1) / [#2](https://github.com/tzervas/agent-harness/issues/2).

## D3 — Python thin package (`agent_harness`) with uv + hatchling

**Context.** v0 needs an installable package and CLI without framework weight or
runtime dependency sprawl.

**Decision.** Ship a thin `agent_harness` package via `pyproject.toml`, **uv** for
lock/sync, **hatchling** as build backend. `requires-python >= 3.14`. Zero runtime
dependencies; stdlib only.

**Why.** Matches repo Python preference, keeps CI and local-ci simple, avoids
premature framework lock-in.

**Alternatives rejected**

| Alternative | Why not |
|---|---|
| Poetry / PDM only | uv is the preferred local+CI toolchain here |
| setuptools-only | hatchling is fine and lighter to configure for pure Python |
| Runtime deps (Click, Typer, httpx, …) | v0 dry-run needs argparse + offline tests only |
| requires-python 3.12 | Project standard is 3.14 preferred |

**Where.** `pyproject.toml`, `agent_harness/`, `scripts/local-ci.sh`.

## D4 — No-op / dry-run CLI first

**Context.** Swarm spawn must be safe in CI and on contributor machines without
paid APIs or network side effects.

**Decision.** CLI commands: `version`, `spawn --issue N --dry-run` (no network),
optional `doctor`. Real provider/GitHub spawn is out of scope for v0 CI.

**Why.** Unblocks board workflow and E2E dry-run epic without secrets or cost.

**Alternatives rejected**

| Alternative | Why not |
|---|---|
| Live GitHub issue fetch in default spawn | Needs tokens; fails offline CI |
| Paid model spawn in CI | Cost + flakiness; human gate |
| No CLI until full orchestrator | Blocks Epic 3/5 scaffolding |

**Where.** `agent_harness/cli.py`, `agent_harness/spawn.py`, [WORKFLOW.md](WORKFLOW.md).

## D5 — Pin GitHub Actions to commit digests

**Context.** Floating tags (`actions/checkout@v4`) can move; supply-chain and
reproducibility matter even for a scaffold.

**Decision.** Pin `actions/checkout` to a full commit SHA (with version comment).
Workflow `permissions: contents: read` by default. Self-hosted path remains gated
by `vars.USE_SELF_HOSTED` (do not enable without human approval).

**Why.** Immutable action versions; least-privilege GITHUB_TOKEN.

**Alternatives rejected**

| Alternative | Why not |
|---|---|
| Floating `@v4` only | Tag can move under us |
| Broad `permissions: write-all` | Unnecessary for docs + test CI |
| Force self-hosted now | Human gate; default `ubuntu-latest` |

**Where.** `.github/workflows/ci.yml`.

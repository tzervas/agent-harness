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

**Where.** [docs/AJL.md](AJL.md), upcoming inventory epic.

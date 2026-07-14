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
| Fork AJL as write base | Policy: AJL read/fork to tzervas only |

**Where.** This repository; relay docs point outward for harness work.

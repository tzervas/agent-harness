# Epics (Wave C)

Board lives on GitHub Issues. **Merges to `dev` leave issues open.** Issues and
epics close only when work reaches **`main`** (see [WORKFLOW.md](WORKFLOW.md)).

There is no separate `ROADMAP.md` — this file plus the GitHub epic issues **are**
the roadmap. Status below is **honest progress**, not issue close state.

| # | Epic | Labels | Depends on | Progress (not board close) |
|---|---|---|---|---|
| [#1](https://github.com/tzervas/agent-harness/issues/1) | Component fitness inventory (generic) | `epic` | — | **Superseded** — exploratory third-party inventory removed; re-open only if needed without external-org framing |
| [#2](https://github.com/tzervas/agent-harness/issues/2) | Fork/integrate selected components under tzervas | `epic` | #1 | **Superseded / cancelled** — no third-party-org fork workflow in-tree |
| [#3](https://github.com/tzervas/agent-harness/issues/3) | Thin CLI and package scaffold | `epic` `cli` | — | **Code landed** (v0.3 CLI/package/`local-ci`/`compose-doctor`); OPEN until formal ship close |
| [#4](https://github.com/tzervas/agent-harness/issues/4) | Integrate tg-agent-relay and agent-mcp by reference | `epic` `docs` | #3 | **compose-doctor** + sibling refs in spawn plan; still compose-by-ref only |
| [#5](https://github.com/tzervas/agent-harness/issues/5) | E2E swarm dry-run path | `epic` | #3, #4 | **Richer dry-run** (roles/exclusive/JSON); live spawn still blocked |

**All five epics are OPEN on the board** as of this writing. Do not treat “code
landed for #3” as “epic closed.”

## Wave intent

1. **Inventory** optional component candidates (document if used).  
2. **Fork** only with human approval → develop on `tzervas` → PR upstream.  
3. **Thin package / CLI** for offline spawn scaffolding.  
4. **Compose** relay + agent-mcp by reference (no product forks).  
5. **E2E dry-run** from swarm-ready issue → spawn template → offline checks.

## Human gates (this wave)

- Do **not** enable `USE_SELF_HOSTED` without further human approval.  
- - No re-vendor of `gha-runner-ctl`; no PyPI release in v0.

## Epic close reminder

- Task issues: close when work reaches **`main`** (`Fixes #N` on promote PR).  
- Epics: close via a final ship issue with `Closes #<epic>` on **`main`**.  
- **`dev` merges leave issues open.**


## 1.0.0 auto-ship (maintainer policy 2026-07-21)

When **all** of the following are true, tag **`v1.0.0`** without waiting for an extra
maintainer "go" (this product is allowed to leave 0.x automatically):

1. Epics #3–#5 acceptance criteria met (or #1–#2 closed as cancelled/superseded).
2. `bash scripts/local-ci.sh` green; fleet-ci + fleet-security green on `main`.
3. Security surface: offline-only default, no secrets in plans, gitleaks/fleet-security clean.
4. Badges present (CI, Security, Runner) and README honesty matches reality.

Until then: continue **0.x** minor/patch releases.

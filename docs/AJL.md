# Average Joe’s Labs (AJL) workflow

You are a **member** of AJL. That does **not** mean we push to AJL as a write base.

## Preferred path

1. **Evaluate** candidate AJL repos (read-only): fitness for harness / orchestration.  
2. **Fork** into `tzervas/<name>` (or your org) when we will extend them.  
3. **Develop** on the fork (`dev` / `feat/*`) with our CI labels and standards.  
4. **PR upstream** to AJL with conventional commits and a clear description.  
5. **Compose** from `agent-harness` via dependency/submodule/docs — avoid deep forks of everything.

## Non-goals

- Direct push to AJL `main`  
- Treating AJL as the only integration branch for tzervas product  
- Silent rewrites without offering upstream PRs when changes are general  
- Real fork without human approval (Epic 1 inventory only unless gate lifts)

## How this fits agent-harness

`agent-harness` may stay a thin orchestrator that **extends** forked AJL components
rather than reimplementing them. Record each fork decision in [DECISIONS.md](DECISIONS.md).

---

## Evaluation checklist

Use this for each candidate repo (read-only). Score then recommend.

| # | Check | Notes |
|---|---|---|
| 1 | **License** compatible with MIT compose (or clearly documented exception) | |
| 2 | **Role fit**: orchestration, swarm board, MCP, spawn, CI, agent runtime? | |
| 3 | **Maintained**: recent commits / issues / releases | |
| 4 | **Surface area**: can we depend without forking? Prefer compose-by-reference | |
| 5 | **Fork cost**: how much would we change vs upstream? | |
| 6 | **Upstream PR path**: would general changes be welcome? | |
| 7 | **Overlap** with `tg-agent-relay` / `agent-mcp` / existing tzervas tools | |
| 8 | **Secrets / network**: can tests stay offline for harness CI? | |
| 9 | **Python 3.14+ / tooling** compatibility if we extend | |
| 10 | **Human gate**: fork only after maintainer approval | |

## Scoring rubric

Score each candidate **0–2** per dimension (0 = poor, 1 = partial, 2 = strong).

| Dimension | Weight | What “2” looks like |
|---|---|---|
| Role fit | ×3 | Directly solves a harness gap |
| Compose-without-fork | ×2 | Usable as dependency/docs reference |
| Maintenance | ×2 | Active, clear ownership |
| Upstream PR hygiene | ×1 | Conventional commits, review culture |
| License clarity | ×2 | Explicit, permissive, no ambiguity |
| Overlap risk | ×2 | Low duplication with relay/MCP (invert: 2 = low overlap) |

**Total** = weighted sum (max 24).

| Score | Recommendation |
|---|---|
| 18–24 | **Fork** candidate (still needs human approval) |
| 12–17 | **Watch** — document; re-evaluate later |
| 0–11 | **Skip** |

Empty shortlist is **acceptable** if the inventory table documents scores and rationale
(see Epic [#1](https://github.com/tzervas/agent-harness/issues/1)).

## Inventory table

**Canonical inventory (Epic 1):** [inventory/AJL_INVENTORY.md](inventory/AJL_INVENTORY.md)
and machine-readable [inventory/ajl_shortlist.json](inventory/ajl_shortlist.json).

Current shortlist status: **empty** (documented rationale in the inventory doc).
Scored candidates are filled there as evaluation proceeds — not in this overview.

| Repo | Role fit | Score | Recommendation | Notes |
|---|---|---|---|---|
| — | — | — | — | See inventory doc; empty shortlist OK |

## `gh` fork and upstream PR commands

```bash
# Read-only browse (example)
gh repo view <ajl-org>/<repo>

# Fork into tzervas (ONLY after human approval)
gh repo fork <ajl-org>/<repo> --org tzervas --clone=false
# or: gh repo fork <ajl-org>/<repo> --clone

# On the fork: develop
git clone git@github.com:tzervas/<repo>.git
cd <repo>
git checkout -b feat/N-short-description
# ... work, conventional commits ...
git push -u origin HEAD
gh pr create --base dev --title "feat: ..." --body "..."

# PR upstream to AJL (from fork)
gh pr create --repo <ajl-org>/<repo> \
  --base main \
  --head tzervas:<branch> \
  --title "feat: ..." \
  --body "$(cat <<'EOF'
## Summary
...

## Why upstream
...

## Test plan
- [ ] offline tests
EOF
)"
```

**Never** `git push` to AJL remotes as the default write base. Fork under `tzervas`,
develop, then open an upstream PR.

## Decision template (copy into DECISIONS.md)

```markdown
## D? — Fork AJL `<repo>` as `tzervas/<name>`

**Context.** <what gap this fills for agent-harness>

**Decision.** Fork `<ajl-org>/<repo>` → `tzervas/<name>`; develop on fork;
PR general fixes upstream. Compose from agent-harness by <dep | docs | submodule>.

**Why.** <score summary; role fit>

**Alternatives rejected**

| Alternative | Why not |
|---|---|
| Depend without fork | <reason> |
| Reimplement in agent-harness | Prefer extend when AJL already solves it |
| Push directly to AJL | Membership ≠ write base |

**Where.** Inventory row; this decision; integration notes if any.

**Human approval.** <date / who>
```

## Related

- Epic [#1](https://github.com/tzervas/agent-harness/issues/1) — inventory  
- Epic [#2](https://github.com/tzervas/agent-harness/issues/2) — fork path  
- [DECISIONS.md](DECISIONS.md) · [INTEGRATIONS.md](INTEGRATIONS.md)

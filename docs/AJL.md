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

## How this fits agent-harness

`agent-harness` may stay a thin orchestrator that **extends** forked AJL components
rather than reimplementing them. Record each fork decision in `docs/DECISIONS.md`.

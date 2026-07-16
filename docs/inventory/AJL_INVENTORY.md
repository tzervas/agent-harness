# AJL inventory (Epic 1)

Machine-readable companion: [`ajl_shortlist.json`](ajl_shortlist.json).  
Checklist + scoring rubric: [AJL.md](../AJL.md).

## Board honesty

| Item | State |
|---|---|
| Epic [#1](https://github.com/tzervas/agent-harness/issues/1) | **OPEN** — inventory scaffolding only; not closed on `dev` merges |
| Real AJL forks | **Blocked** by human gate (Epic [#2](https://github.com/tzervas/agent-harness/issues/2)) |
| Shortlist | **Empty** (documented; acceptable per epic acceptance) |

## Inventory table

| Repo | Role fit | Score (0–24) | Recommendation | Notes |
|---|---|---|---|---|
| — | — | — | — | No candidates scored yet |

## Empty shortlist rationale

1. **Scaffold first.** Wave C shipped the offline CLI / package (Epic 3 code path) before a scored AJL survey.  
2. **No silent forks.** Empty shortlist avoids inventing “fork” rows without read-only evaluation evidence.  
3. **Epic acceptance.** Empty shortlist is explicitly allowed when rationale is documented.  
4. **Next step (not this PR).** Maintainers or a `swarm-ready` child issue can fill rows via read-only `gh repo view` / public docs, using the rubric in [AJL.md](../AJL.md). Any **fork** recommendation still needs a DECISIONS.md entry and human approval before Epic 2 work.

## How to add a candidate

1. Score with the rubric in [AJL.md](../AJL.md) (max 24).  
2. Add a row to the table above.  
3. Append an object to `candidates` in `ajl_shortlist.json`:

```json
{
  "repo": "org/name",
  "role_fit": "short phrase",
  "score": 0,
  "recommendation": "skip | watch | fork",
  "notes": "why"
}
```

4. If `recommendation` is `fork`, copy the decision template from AJL.md into [DECISIONS.md](../DECISIONS.md) and wait for human approval before any `gh repo fork`.

## Related

- Epic [#1](https://github.com/tzervas/agent-harness/issues/1) · Epic [#2](https://github.com/tzervas/agent-harness/issues/2)  
- [AJL.md](../AJL.md) · [EPICS.md](../EPICS.md) · [DECISIONS.md](../DECISIONS.md)

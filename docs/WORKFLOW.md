# Workflow

Mirrors [tg-agent-relay’s process](https://github.com/tzervas/tg-agent-relay/blob/main/docs/WORKFLOW.md)
with this product’s boundaries.

## Branches

- **`dev`** — persistent integration; feature PRs land here  
- **`main`** — stable; **PR only** (promote from `dev`)  
- **`feat/N-*`** — cut from `dev`  

## Issue close policy

| Kind | Closes when |
|---|---|
| Task issues | Work reaches **`main`** (`Fixes #N` on the promote PR / main merge) |
| Epics | Final ship issue with `Closes #<epic>` on **`main`** |

Merges to **`dev` leave issues open**.

## Cost lanes

| Lane | Use |
|---|---|
| **Build** (preferred) | Implementation swarms |
| **Flagship** | Architecture joins only |
| **Fast** | Trivial docs / renames |

## Swarm issue minimum

- Parent epic  
- User story + acceptance criteria  
- Exclusive write ownership  
- Out of scope  
- Offline tests  
- PR body includes `Fixes #N`  

## Self-hosted CI

One host via [gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).  
Org registration for multi-repo sharing; personal user repos cannot use another
org’s runners while remaining outside that org.

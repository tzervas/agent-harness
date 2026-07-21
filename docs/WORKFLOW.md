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

Merges to **`dev` leave issues open**. Do not close issues or epics on dev-only merges.

## Labels

| Label | Use |
|---|---|
| `epic` | Multi-issue initiative |
| `swarm-ready` | Exclusive-file Build-lane task ready for agents |
| `docs` | Documentation work |
| `cli` | Thin package / CLI work |

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
- PR body includes `Fixes #N` (closes only when that PR lands on **`main`**)  

Use the **Swarm task** issue template (`.github/ISSUE_TEMPLATE/swarm_task.yml`).

## Spawn template (local dry-run)

Offline plan only — **no network, no paid API**.

```bash
# Show package version (from VERSION / package metadata)
uv run agent-harness version

# Build a spawn plan for issue N without calling GitHub or providers
uv run agent-harness spawn --issue N --dry-run

# Optional environment checks
uv run agent-harness doctor
```

### Spawn plan fields (dry-run JSON / text)

| Field | Meaning |
|---|---|
| `issue` | Issue number |
| `mode` | `dry-run` |
| `network` | always `false` in dry-run |
| `lane` | default `build` |
| `write_ownership` | filled by swarm issue body (not fetched in offline mode) |
| `commands` | suggested local validation (`scripts/local-ci.sh`) |

Example:

```text
spawn plan (dry-run)
  issue:        #3
  mode:         dry-run
  network:      false
  lane:         build
  validate:     bash scripts/local-ci.sh
  note:         offline; no GitHub fetch; fill exclusive files from issue body
```

## Epic close reminder

- Task: `Fixes #N` closes on **`main`** only.  
- Epic: ship issue with `Closes #<epic>` on **`main`**.  
- **`dev` merges leave the board open.**

## Commits and version bumps

- Prefer [Conventional Commits](https://www.conventionalcommits.org/).  
- Optional Commitizen config: [`.cz.toml`](../.cz.toml) (aligned with gha-runner-ctl style).  
- Keep `VERSION`, `pyproject.toml`, and `.cz.toml` in sync (currently **0.2.0** alpha).
  Tag format `v$version`; do not tag without a ship decision and CHANGELOG entry.

## Self-hosted CI

One host via [gha-runner-ctl](https://github.com/tzervas/gha-runner-ctl).  
Org registration for multi-repo sharing; personal user repos cannot use another
org’s runners while remaining outside that org.

**Human gate:** do not set `USE_SELF_HOSTED=true` without maintainer approval.

## Related

- [EPICS.md](EPICS.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [INTEGRATIONS.md](INTEGRATIONS.md)

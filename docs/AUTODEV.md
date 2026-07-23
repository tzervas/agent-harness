# Autodev loop — ephemeral sessions (issue #24)

Resolves the hard limit documented in **agent-coop#17**: nothing can wake a *stopped*
coding session from inside agent-coop. Spawning is **agent-harness** territory
(ADR-0002).

## Architecture

```
  agent-harness supervisor (long-lived)
        │  unit queue (local) + coop bus (durable)
        │  claim lease → spawn → reap → post result
        ▼
  ephemeral sessions
     ├── mock   (tests / offline)
     ├── claude -p  (print / non-interactive)
     └── grok --prompt-file
```

**Sessions are short-lived on purpose.** Context exhaustion is a work boundary, not an outage.
The dying session leaves a **pointer** handoff (file path), not a 500-char dump of state.

## CLI

```bash
# Offline plan (unchanged)
uv run agent-harness spawn --issue 24 --dry-run

# Enqueue a unit (pointer-first)
uv run agent-harness enqueue \
  --title "implement feature X" \
  --pointer /path/to/handoff-or-plan.md \
  --provider mock

# Process one unit
uv run agent-harness loop --once --no-lease

# Watch queue (mock or live providers)
uv run agent-harness loop --poll 15 --provider mock   # provider is per-unit

# Board
uv run agent-harness status
```

Environment:

| Var | Meaning |
|-----|---------|
| `AGENT_HARNESS_HOME` | State root (default `~/.local/state/agent-harness`) |
| `AGENT_COOP_HOME` | Bus home (shared with agent-coop; use `.coop`) |
| `AGENT_COOP_AGENT` | Identity for bus posts from supervisor (default `harness`) |

## Design choices (settled for v0.4)

| Question | Choice |
|----------|--------|
| Session granularity | **One session per unit of work** (lease + pointer) |
| Handoff format | **Pointer file**; bus body references id + path |
| Reaping | **TTL leases** via coop; supervisor releases on completion; no active steal |
| Failure budget | **max_attempts** (default 3) then `block` on bus + `escalated` state |
| Control plane | **One supervisor**; bus is the durable queue; relay stays observe-only |

## Live providers

- **claude:** `claude -p "<prompt>" --bare` (non-interactive). Requires Claude Code on PATH.
- **grok:** `grok --prompt-file <path>` (single-turn). Requires Grok CLI on PATH.
- **mock:** writes a result file; used in tests and dry fleets.

Live spawn spends tokens. Prefer `mock` in CI.

## TUI

v0.4 ships a **stdlib status board** (`agent-harness status`). A full interactive TUI should
**compose cabal-devmelopner’s textual TUI** (fleet prior art) rather than invent a second one —
tracked as follow-up under #24 comments / epic board. The supervisor state is JSON under
`$AGENT_HARNESS_HOME` so any TUI can read it without a second control plane.

## Relation to agent-coop timers

| Process | Role |
|---------|------|
| `agent-coop-auto.timer` / `coop-daemon` | Mechanical bus/sync — **no LLM** |
| Claude/Grok session ticks | Self-prompt **inside running sessions** |
| **agent-harness loop** | Spawns **new** short sessions when work is queued |

## Safety

- No secrets in unit JSON or bus bodies.
- Lease exit **3** → re-queue / backoff (never retry-to-win).
- Do not run parallel supervisors against the same `AGENT_HARNESS_HOME`.

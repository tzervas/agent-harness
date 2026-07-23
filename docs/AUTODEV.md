# Autodev loop — ephemeral sessions, supervised

Resolution of [#24](https://github.com/tzervas/agent-harness/issues/24), which is in
turn the resolution of [`agent-coop#17`](https://github.com/tzervas/agent-coop/issues/17).

## The limit that forces this design

agent-coop#17 measured a hard limit: **nothing can wake a stopped session.** A hook
injects into a session that is already running; *starting* one is spawning, which
ADR-0002 assigns to this repo.

So a loop that spans running sessions degrades the moment a session ends — and
sessions end constantly, because they exhaust context.

## The inversion

Stop keeping sessions alive. Make them short-lived on purpose and supervise them.
The loop lives in the supervisor, not in the sessions.

```
  agent-harness (supervisor, long-lived)
        │  reads work            ┌──────────────┐
        ├───────────────────────►│  agent-coop  │  bus + leases + ledger
        │  spawns / reaps        │  (dependency)│  = durable work queue
        ▼                        └──────────────┘
  ephemeral sessions ── claude ──┐        ▲
                    └── grok ────┴────────┘  results posted back to the bus
```

Context exhaustion becomes a work boundary rather than an outage.

## agent-coop is a dependency, not a component

Per `agent-coop/docs/ADR-0002`, agent-coop owns leases, the bus and ff-only git sync —
nothing else. `agent_harness/coop.py` drives the `coop` CLI as a subprocess and
reimplements none of it. There stays exactly one lease authority and one work queue.

A session that dies mid-task leaves a lease with a TTL, so the work becomes
reclaimable automatically. That is precisely what TTL'd advisory leases are for, and
it is why the supervisor keeps no separate bookkeeping.

## The four open questions, settled

**1. Session granularity — one ephemeral session per leased component.**
The lease already bounds the work and already carries a TTL. Finer granularity pays
spawn overhead for nothing; coarser granularity walks back into mid-task context
exhaustion. Two units contending for one component are collapsed up front
(`dedupe_by_key`) so the loser does not look like a failure.

**2. Handoff format — pointer, not payload.**
The bus body limit is 500 characters, measured; a handoff does not fit and an
over-long body is *rejected*, losing the message entirely. The payload is a file
under `--handoff-dir`; the bus message carries its path. Existing fleet practice
already leans this way.

A session that exits without writing a handoff still gets a stub, so its successor
is never handed silence.

**3. Reaping vs TTL — release only what you claimed, for a session you watched exit.**
Everything else waits for TTL expiry. Active reaping of another agent's lease cannot
distinguish "dead" from "merely slow", and stealing a lease from a slow session is
how two agents end up writing the same file.

**4. Failure budget — escalate, do not respawn forever.**
`--failure-budget` consecutive failures on one unit (default 3) stops respawning and
posts a `block` message naming the unit. Silence is not a result.

## Provider routing

Both CLIs expose a single-shot headless mode, which is what makes an ephemeral
session possible at all:

```bash
claude -p "<prompt>" --output-format json
grok   -p "<prompt>" --output-format json
```

Routing inputs, per #24: remaining budget per provider, task shape (lane),
capability, and lease conflicts. A lane no installed provider can serve raises
rather than silently downgrading the tier — a wrong-tier session is worse than an
honest escalation.

## The autoprompt

A spawned session has no conversational history, so `agent_harness/autoprompt.py`
puts everything it needs into one string: the task, the coordination discipline
(exit 3 is back-off, never steal, peek-then-drain), the validation gate, the handoff
obligation, and the exit contract.

It tells the session plainly that it is short-lived and that its exit code is the
signal the supervisor acts on.

## Usage

```bash
# Plan only — claims no leases, spawns nothing. Safe in CI.
agent-harness loop --units backlog.json

# Actually claim leases and spawn sessions.
agent-harness loop --units backlog.json --live \
  --failure-budget 3 --handoff-dir .coop/handoff

# Keep going until nothing is worth attempting.
agent-harness loop --units backlog.json --live --watch --interval 30
```

Backlog format — a JSON list, or `{"units": [...]}`:

```json
[
  {
    "uid": "fix-parser",
    "repo": "mycelium-lang",
    "component": "mycelium-l1/src/elab.rs",
    "task": "Add the host-call table and dispatch for wild:name nodes.",
    "issue": 16,
    "lane": "build",
    "validate": "bash scripts/local-ci.sh",
    "ttl": 3600
  }
]
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Every unit finished, was planned, or backed off a held lease |
| 1 | A unit escalated, or no provider could serve it |
| 2 | Bad invocation (missing backlog, malformed `--budget`, no `coop` for `--live`) |

A held lease is **not** an error. Backing off is the correct behaviour, so it does
not fail the run.

## What is deliberately not built

- **No second scheduler.** grok already hit this on the fleet side: parallel `up`
  loops held a registration lock and starved everyone. One supervisor.
- **No second control plane.** tg-agent-relay stays observe-only.
- **No new work queue.** The bus is the queue.

# Vision

## Goals

1. **Orchestrate** multi-agent coding work with clear roles (orchestrator vs swarm implementers).
2. **Compose** existing `tzervas` capabilities (relay, MCP, security tooling) instead of rewriting them.
3. **Stay cheap enough to scale**: Build-lane models for bulk implementation; flagship only for hard joins.
4. **Honest board**: issues close when work reaches `main`; epics close via a final ship issue.
5. **Local-first quality** with optional shared self-hosted runners.

## Non-goals

- Replacing Telegram runtime (`tg-agent-relay` remains the product surface for phone ↔ agent).
- Pushing to third-party orgs as a default write base.
- Fleet-scale runner infrastructure (one well-run host is enough).
- Framework-heavy stacks when a thin harness will do.

## Success (v0)

- Documented architecture and swarm workflow  
- Skeleton package / CLI that can spawn a no-op swarm task  
- Integration notes for tg-agent-relay + agent-mcp  
- CI workflow that can use shared labels  

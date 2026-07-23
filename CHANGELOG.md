# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Ephemeral-session autoloop planner** (`agent_harness/loop.py`, `agent-harness loop`) —
  plans a development task across repeated *ephemeral* sessions, each a fresh session given
  an **autoprompt** derived from the task and the prior iteration's reported outcome.
  Offline dry-run only, matching `spawn`: it plans an autoloop, it does not run one.
  - **Bounded by construction** — `--max-iterations` is required, defaults to 5 and is hard
    capped at 100. An autoloop that stops "when the model decides it is done" is an
    unbounded spend, and a loop unable to make progress will burn the budget proving it.
  - **Idle-aware** — `--stop-after-idle` requires N *consecutive* no-progress rounds
    ("loop until dry") rather than quitting on the first quiet one. A value that could
    never fire (greater than `--max-iterations`) is rejected, since a stop condition that
    cannot trigger reads as protection while providing none.
  - **Never-silent** — every plan enumerates its stop conditions up front.
  - **Deterministic** — session ids hash from task+index with no clock or randomness, so a
    plan is reproducible and testable.
  - The resumed-iteration autoprompt explicitly tells the session it did *not* perform the
    carried work and must verify state itself, so it cannot re-report a previous
    iteration's success as its own.
- `tests/test_loop.py` — 17 offline tests covering bounds, determinism, session isolation,
  refusal of live execution, and every validation path.

## [0.3.0] — 2026-07-21

### Added
- **spawn plan v1:** roles (orchestrator/implementer/reviewer), exclusive path globs,
  compose sibling refs, worktree hint — still offline-only dry-run.
- **`--json`** on `spawn` for machine-readable plans (E2E dry-run surface).
- **`--exclusive GLOB`** (repeatable) to pin leaf ownership in the plan.
- **`compose-doctor`** advisory offline sibling discovery (never vendors; never fails on missing).

### Changed
- Version **0.2.0 → 0.3.0** (minor: plan surface + compose doctor).
- Epics #1/#2 remain superseded (no third-party-org fork workflow).
- 1.0.0 may auto-tag when epics #3–#5 acceptance + CI/security bar met (see docs/EPICS.md).

## [0.2.0] — 2026-07-21

### Removed
- Average Joe's Labs (AJL) exploratory inventory docs, shortlist JSON, and offline loader.
  That work was only for not re-doing team research in another org; not product surface.

### Changed
- **docs/INTEGRATIONS.md** — added a compose-pointer honesty note to the
  `cabal-devmelopner` section: cabal is pre-1.0 with no released interface, and
  "cabal may drive harness dry-runs" is a doc-only forward reference, not a
  shipped or contract-tested adapter.
- **Version** — `0.1.0` → **`0.2.0`** (alpha; VERSION/pyproject/.cz.toml/local-ci
  gate kept in sync; board honesty unchanged: epics #1–#5 remain OPEN).

## [0.1.0] — 2026-07-16

### Added

- **Production polish (P28a)** — product-ready offline harness docs and agent surface.
- **AGENTS.md** — fractal-lite agent rules: PR tiers (`Refs` vs `Closes`), local-ci,
  no secrets, compose-by-reference pointers.
- **CLAUDE.md** — commands map for coding assistants (`uv sync`, ruff, pytest, CLI smoke).
- **CHANGELOG.md** — versioned release notes for 0.x.
- **`.pre-commit-config.yaml`** — optional gitleaks + basic file hooks + ruff.
- **INTEGRATIONS** — compose guide for [tz-forge](https://github.com/tzervas/tz-forge),
  tg-agent-relay, agent-mcp, and cabal-devmelopner.

### Changed

- **README** — clear product statement and offline 5-minute path with expected output.
- **Version** — `0.0.1-dev` → **`0.1.0`** (alpha; honest board: epics #1–#5 remain OPEN).
- **local-ci** — requires AGENTS.md, CLAUDE.md, CHANGELOG.md; version gate matches `0.1.0`;
  doctor is a hard gate (no longer soft-failed).

### Notes

- Runtime remains **stdlib-only** (zero dependencies). CLI: `version`, `spawn --dry-run`,
  `doctor`. Live spawn is not implemented.
- This is an **alpha 0.x** release: usable offline scaffold, not a full swarm platform.

## [0.0.1-dev] — 2026-07-15

### Added

- Thin offline CLI (`version` / `spawn --dry-run` / `doctor`).
- Epic 1 inventory stub (later removed).
- Docs pack: VISION, WORKFLOW, ARCHITECTURE, DECISIONS, EPICS, INTEGRATIONS.
- `scripts/local-ci.sh` offline gate (ruff + pytest + CLI smoke).
- Fleet standards workflows and badges (P26).
- REUSE / SPDX license bootstrap.

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Epic 1 AJL inventory stub + offline loader tests.
- Docs pack: VISION, WORKFLOW, ARCHITECTURE, AJL, DECISIONS, EPICS, INTEGRATIONS.
- `scripts/local-ci.sh` offline gate (ruff + pytest + CLI smoke).
- Fleet standards workflows and badges (P26).
- REUSE / SPDX license bootstrap.

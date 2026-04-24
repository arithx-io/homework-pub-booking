# Changelog

All changes to the homework after a cohort's release tag get documented here.
Students are told to `git pull` when a new entry appears.

## [2026.04.0] — unreleased (first cohort)

Initial release for Nebius Academy Module 1 Week 5.

### Structure

- Five exercises (Ex5–Ex9) extending the `examples/pub_booking` scenario
  from `sovereign-agent == 0.2.0`.
- Pinned framework version: `sovereign-agent == 0.2.0` exactly. Not a compatible-release
  pin — the grader depends on exact reproducibility for this cohort.
- Scaffolds under `starter/`, grader under `grader/`, reflection templates
  under `answers/`.

### Tooling

- `make setup` → `uv sync --all-groups` + `.env` bootstrap.
- `make verify` → preflight (ruff, pytest collection, imports) + live
  1-token Nebius round-trip.
- `make check-submit` → local grader run (advisory).
- `make ex{5,6,7,8,9}` → per-exercise runners.

### CI

- `ci.yml` runs on every PR: lint, format-check, public tests, offline
  scaffold runs. No secrets needed — offline Fake LLM mode.
- `grade.yml` runs manually or at deadline: the authoritative grader,
  with Nebius + Speechmatics secrets from GitHub, materialises private
  tests from a separate grader repo.

## Unreleased

Entries here will be added if/when a bug fix lands during the cohort
window. Tagging convention: `v2026.04.0.N` for patch N.

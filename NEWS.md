# News

User-facing changes, newest release first. Add each release under a `##`
heading; use `###` for categories. The latest released version (not the
Unreleased block) is automatically shown in the README. Keep internal plans
and evaluation artifacts out of this file.

<!-- UNRELEASED:START -->
## Unreleased

### Added

- Add automatic NEWS unreleased updates
- Add one-command remote skill installation

<!-- UNRELEASED:END -->

## v0.1.0-beta (2026-10-30)

### Added

- Four review probes: behavior correctness, test coverage, repository rules,
  and impact analysis.
- Portable skill source in `skills/code-review/`, with separate Claude Code
  and Codex reviewer adapters in `adapters/`.
- JSON-derived report sections and merge gates, with an optional independent
  reviewer.
- A unified installer for `claude-code`, `codex`, or both, with dry-run,
  conflict protection, and timestamped backups under `--force`.

### Changed

- Severity now uses three levels: `high`, `medium`, and `low`. Earlier
  four-level records require an explicit migration or a new review.
- Findings that depend on an unresolved contract conflict are capped at
  `medium` and marked as requiring contract confirmation.

### Packaging

- Added an MIT license, version file, and offline regression tests.
- Internal design documents and evaluation artifacts stay outside the
  published tree.

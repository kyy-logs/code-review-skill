# News

User-facing changes, newest release first. Add each release under a `##`
heading; use `###` for categories. The first release is automatically shown
in the README. Keep internal plans and evaluation artifacts out of this file.

## v0.1.0-beta (2026-10-30)

### Added

- Four review probes: behavior correctness, test coverage, repository rules,
  and impact analysis.
- Portable skill source in `skills/code-review/`, with a separate Claude Code
  reviewer adapter in `adapters/claude-code/`.
- JSON-derived report sections and merge gates, with an optional independent
  reviewer.

### Changed

- Severity now uses three levels: `high`, `medium`, and `low`. Earlier
  four-level records require an explicit migration or a new review.
- Findings that depend on an unresolved contract conflict are capped at
  `medium` and marked as requiring contract confirmation.

### Packaging

- Added an MIT license, version file, and offline regression tests.
- Internal design documents and evaluation artifacts stay outside the
  published tree.

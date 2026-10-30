# code-review-skill

English | [简体中文](README.zh-CN.md)

**Evidence-backed code review. Static-first, probe-driven, and gated.**

The skill source lives in [`skills/code-review/`](skills/code-review/), independently of any host's installation directory. Reviewer adapters for Claude Code and Codex are included in [`adapters/`](adapters/). The current version is a beta candidate; see [VERSION](VERSION).

[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-6B4FBB?style=flat-square)](https://claude.com/claude-code)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-standard-1f6feb?style=flat-square)](https://agentskills.io)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Static-first](https://img.shields.io/badge/review-static--first-2ea44f?style=flat-square)](#what-this-is-not)

Most AI reviews stop at “this looks risky.” This skill produces a review you can audit: every finding points to a location, a contract or code path, and a severity; every gate decision is rendered from machine-readable JSON. It reads the diff, surrounding source, tests, and project rules — no build, test run, or coverage report required.

It never modifies the code under review.

## Latest news

<!-- NEWS:START -->
### v0.1.0-beta (2026-10-30)

#### Added

- Four review probes: behavior correctness, test coverage, repository rules,
  and impact analysis.
- Portable skill source in `skills/code-review/`, with separate Claude Code
  and Codex reviewer adapters in `adapters/`.
- JSON-derived report sections and merge gates, with an optional independent
  reviewer.
- A unified installer for `claude-code`, `codex`, or both, with dry-run,
  conflict protection, and timestamped backups under `--force`.

#### Changed

- Severity now uses three levels: `high`, `medium`, and `low`. Earlier
  four-level records require an explicit migration or a new review.
- Findings that depend on an unresolved contract conflict are capped at
  `medium` and marked as requiring contract confirmation.

#### Packaging

- Added an MIT license, version file, and offline regression tests.
- Internal design documents and evaluation artifacts stay outside the
  published tree.

[Full update history](NEWS.md)
<!-- NEWS:END -->

## Release status

`v0.1.0-beta` — this is a test release. The probe contract, report schema, and
gate behavior may change before 1.0.

- **Severity is three levels:** `high`, `medium`, `low`. Records written by the
  earlier four-level version, including any `critical` value, are **not
  compatible**; `collect-metrics` rejects them. Re-run the review or migrate the
  records before using them with this release.
- **Scope:** static-first review with four probes, an optional independent
  reviewer, and JSON-derived report/gate output. It does not replace tests, CI,
  or human review.
- **Validation:** 43 offline pipeline and installation tests; a clean-project end-to-end run with
  the reviewer and a failing gate; additional probe/reviewer smokes. These are
  regression checks, not a general recall claim. Concurrency-defect detection
  has not been validated.

## Contents

- [Latest news](#latest-news)
- [Release status](#release-status)
- [Why this skill](#why-this-skill)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Evidence contract](#evidence-contract)
- [Configuration](#configuration)
- [Independent reviewer](#independent-reviewer)
- [What this is not](#what-this-is-not)
- [Validation](#validation)
- [Requirements](#requirements)
- [Repository layout](#repository-layout)
- [Contributing](#contributing)
- [License](#license)

## Why this skill

| | |
|---|---|
| **Static-first** | Works on a fresh clone or a partial checkout. Coverage is optional, not a prerequisite. |
| **Evidence contract** | A finding without a location, summary, and checkable evidence is not a finding. |
| **Four probes** | Behavior, tests, rules, and impact are separate questions with separate reports. |
| **Independent reviewer** | Optional second context that sees the frozen inputs and raw findings — not the expected answer. |
| **Machine-checkable gate** | Counts and blockers come from JSON, not from prose the model retyped. |
| **Auditable output** | The human report and the JSON records are rendered from the same source and verified against each other. |

## Quick start

### Install

The repository keeps the portable skill in `skills/code-review/`; installation copies it and the matching reviewer adapter into your project. The installer does not overwrite existing files by default.

Run this command **inside your project** to install the skill and Codex reviewer together:

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/kyy-logs/code-review-skill/feat/behavior-review-probe/scripts/install-remote.py', timeout=30).read())" --agent codex
```

Requires Python 3.9+ and Git on `PATH`; use `python3` if that is your Python command. Replace `codex` with `claude-code` or `both` to select another host. The entry downloads this feature branch into a temporary directory, runs the installer, and removes the checkout afterward. You do not need to clone or enter this repository yourself.

Append `--dry-run` to preview, `--project "/path/to/your-project"` to choose another project, or `--ref <branch-or-tag>` to select a source version that includes the installer. Until this change is merged, the remote entry and its default source are on `feat/behavior-review-probe`.

For a local checkout:

```bash
git clone --branch feat/behavior-review-probe https://github.com/kyy-logs/code-review-skill.git
cd code-review-skill
python scripts/install.py --agent both --project /path/to/your-project
```

Or use the shell wrapper:

```bash
bash scripts/install --agent codex --project /path/to/your-project
```

Host layouts:

| Host | Skill | Reviewer adapter | Dispatch |
|---|---|---|---|
| Claude Code | `.claude/skills/code-review/` | `.claude/agents/reviewer.md` | `subagent_type: reviewer` |
| Codex | `.agents/skills/code-review/` | `.codex/agents/reviewer.toml` | custom agent `reviewer` (`agent_type: reviewer`) |

`--agent` accepts `claude-code`, `codex`, or `both`. Existing files are protected: the installer exits with a conflict list; `--force` backs up the existing target before replacing it. `--dry-run` prints the plan. It never edits `.codex/config.toml` or other agents.

`npx -y skills add ... --agent codex --yes` installs the skill only; it does not install the reviewer adapter. Use the installer above for the independent reviewer. Node.js 22.20+ is only needed for that optional `npx` path.

For another host, install `skills/code-review/` into that host's skill directory and provide its own independent-context mechanism. Only the Claude Code and Codex adapters are supplied.

Both copies are needed for the full workflow: installing the skill alone does not register the independent reviewer. If Python cannot import PyYAML, install it with `python -m pip install PyYAML` in the interpreter used by the skill; `CODE_REVIEW_PYTHON` can select another interpreter.

### Run

Ask in Claude Code:

```text
Review these changes with code-review.
```

Or invoke the skill directly:

```text
/code-review
```

For a fixed range:

```text
Use code-review on commits abc123..def456
```

The skill supports two review modes:

- `worktree` — staged, unstaged, and untracked changes against the current `HEAD`.
- `commits` — a fixed `base..head` range.

### Read the result

```text
docs/work/active/{slug}/
├── code-review.md      # human report
├── reviewer.json       # independent reviewer verdicts (optional)
└── probes/
    ├── behavior-review.json
    ├── test-coverage.json
    ├── repo-guard.json
    └── impact-analysis.json
```

## How it works

```text
scope ──► probes ──► sync ──► reviewer? ──► reconcile ──► report ──► gate
```

1. **Scope** — determine `worktree` or `commits`; record base and head as commit IDs.
2. **Probes** — run in registry order by one executor, reusing the same scope and diff.
3. **Sync** — validate probe JSON and derive counts with `collect-metrics`.
4. **Reviewer (optional)** — dispatch only when `review-mode` returns `run`.
5. **Reconcile** — high findings must be closed or explicitly rejected.
6. **Report** — render the human report’s fact sections from JSON, then verify them.
7. **Gate** — required-probe failures and open high findings block the merge.

### The four probes

| Probe | Required | Question it answers |
|---|---|---|
| `behavior-review` | yes | Does the changed behavior match its actual contract and implementation path? |
| `test-coverage` | yes | Are the tests meaningful, and is incremental coverage measured when data exists? |
| `repo-guard` | yes | Does the change violate repository or project rules? |
| `impact-analysis` | no | Who calls this, what contracts change, and what is the performance/architecture blast radius? |

Probes are intentionally narrow. `behavior-review` is not a linter, and `repo-guard` is not a general bug scanner.

## Evidence contract

Every finding records:

| Field | Meaning |
|---|---|
| `location` | `path:line`, or file level with a reason |
| `summary` | What is wrong — not “consider improving” |
| `evidence` | Contract, code path, test output, or rule ID |
| `severity` | `high` / `medium` / `low` |
| `status` | `open` / `reconciled` / `wontfix` / `false-positive` |

High-severity findings must cite the actual method signature and the contract they violate, or a concrete code path. A hunch is capped at `medium` until the evidence is checked.

## Configuration

`references/probes.yaml` controls the probe registry and reviewer policy:

```yaml
reviewer:
  mode: auto        # auto | always | never
  skip_when:
    - no_findings
    - only_docs
  policy: strict    # strict | advisory
```

Project-specific rules can live in `.code-review/rules/`, or be pointed to with `CODE_REVIEW_RULES_DIR`:

```bash
export CODE_REVIEW_RULES_DIR=/path/to/rules
```

A project rule package **replaces** the built-in package; it is not merged with it.

## Independent reviewer

`skills/code-review/references/reviewer.md` is the host-neutral reviewer script. `adapters/claude-code/reviewer.md` is the Claude Code adapter (installed at `.claude/agents/reviewer.md`); `adapters/codex/reviewer.toml` is the Codex custom-agent definition (installed at `.codex/agents/reviewer.toml`). Both adapters only provide host routing and point back to the same reviewer script.

The reviewer gets the frozen skill, the case inputs, and the raw probe bundle — not reference comments, expected answers, or prior reports. If the host cannot provide a fresh context, record that limitation; do not fabricate a verdict.

## What this is not

- Not a replacement for tests, CI, or human review.
- Not a guarantee that a clean report means the change is correct.
- Not a coverage tool: coverage is used when provided, not required.
- Not a fixer: it does not modify the code under review.

## Validation

<details>
<summary>11-case historical Java regression (2026-10-29)</summary>

- Baseline: commit `494a39bb`, before `behavior-review` was extracted into a standalone probe. The snapshot validates the shared finding and gate contract, not the four-probe split itself.
- 11/11 cases completed; reviewer off; static review.
- Original behavior targets: 5/5 hit; including two independently confirmed edge cases, 5/7 required targets were found.
- Clean and fixed controls: 4/4 passed without false blocking.
- Two confirmed edge-case misses remain: legal input formatting in a parser, and a JSON representation round-trip in command rendering.
- 33 raw findings: 8 high, 20 medium, 5 low; 0 confirmed false positives, with unverified items still open.
- The full merge gate was not run.

Risk areas exercised by these cases:

| Risk area | Cases | Observed result |
|---|---|---|
| Resource lifecycle | DBeaver | Found an input stream left open after copying; confirmed target. |
| Execution logic | Kestra, Keycloak guides | Found duplicate interpreter/command assembly in Kestra; confirmed target. Also reported switch fall-through in Keycloak, with downstream impact only partly supported. |
| Input boundaries and value handling | Lang-1, Spring AI Alibaba | Found hexadecimal overflow handling and blank-string sentinel problems; confirmed targets. The leading-zero return-type finding remained a contract dispute and was rated too high. |
| Permissions and data scope | Keycloak groups (m01), Elasticsearch | Found authorization resource IDs used as group IDs; confirmed target. The non-default filesystem permission-bypass candidate still needs threat-model and exploitability evidence. |
| API compatibility | Kestra | Identified public SPI return-type changes and new abstract methods; compatibility break supported, affected external plugins not measured. |
| Cache and state consistency | Keycloak login cache (m02) | Reported an invalidation risk involving organization-wrapped models; runtime consequences remain unverified. |
| Performance and repeated work | Elasticsearch, Kestra, Keycloak login cache | Reported logging overhead, repeated rendering/downloads, and extra lookups; performance impact was not benchmarked. |
| Test quality and regression protection | DBeaver, Keycloak, Kestra | Identified missing branch tests, tests bypassing the changed production entry point, and incorrect cleanup or cache-invalidation coverage. |

The two confirmed misses were Keycloak's valid `tileVisible = "false"`
syntax bypassing validation, and Kestra's JSON render/parse round-trip
corrupting command values containing quotes, backslashes, or newlines.

The four controls checked false alarms: the Lang-1 fix, normal pagination,
normal tag normalization, and a valid login-cache delegation path that should
not be reported as recursion. Passing a control does not establish that its
entire change is defect-free.

The evaluation harness and raw reports are kept out of the published repository. This snapshot is a regression result, not a claim of general recall.

</details>

## Requirements

- Claude Code with Agent Skills support, or Codex with custom-agent support.
- Bash, Git, awk, grep, sed.
- Python 3.9+; installation uses the standard library. PyYAML is required to run the review scripts for report parsing and metrics.
- Node.js 22.20+ only if you use the optional `npx skills` shortcut for a skill-only install.

## Repository layout

```text
code-review-skill/
├── README.md
├── README.zh-CN.md
├── NEWS.md
├── LICENSE
├── VERSION
├── .github/workflows/sync-news.yml
├── scripts/
│   ├── install
│   ├── install.py
│   ├── install-remote.py
│   └── sync-news.py
├── skills/
│   └── code-review/
│       ├── SKILL.md
│       ├── assets/code-review.md
│       ├── references/
│       │   ├── probes.yaml
│       │   ├── output-schema.md
│       │   ├── reviewer.md
│       │   ├── probes/
│       │   └── rules/
│       └── scripts/
│           ├── review-mode
│           ├── collect-metrics
│           ├── lib-metrics
│           ├── rule-grep
│           └── sync-results.py
├── adapters/
│   ├── claude-code/reviewer.md
│   └── codex/reviewer.toml
└── tests/
```

## Contributing

Issues and pull requests are welcome. For a behavior change, include:

- the review target (repo and base/head),
- the expected finding or gate decision,
- the observed finding or gate decision,
- the evidence that distinguishes them.

For a probe or schema change, update the probe document, the output contract, and the affected scripts together.

Run the offline suite with `python -m unittest discover -s tests -v`. Set `CODE_REVIEW_TEST_BASH` to a Bash executable to include shell and installation checks; see [tests/README.md](tests/README.md). These checks do not call models or establish defect recall.

Record user-facing changes in [NEWS.md](NEWS.md), newest release first. Pushes
that change NEWS or its synchronizer update the README's marked news preview
automatically. Only that preview is generated; edit the rest of this README
normally. You can also run `python scripts/sync-news.py` locally, or add
`--check` to detect a stale preview without changing files. Automatic commits
use the built-in `GITHUB_TOKEN`; branch rules must allow that bot to push.
Keep [README.zh-CN.md](README.zh-CN.md) aligned when changing this document;
the Chinese translation, including its news summary, is maintained manually.

## License

This repository is distributed under the [MIT License](LICENSE).

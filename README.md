# code-review-skill

**Evidence-backed code review for Claude Code. Static-first, probe-driven, and gated.**

[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-6B4FBB?style=flat-square)](https://claude.com/claude-code)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-standard-1f6feb?style=flat-square)](https://agentskills.io)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Static-first](https://img.shields.io/badge/review-static--first-2ea44f?style=flat-square)](#what-this-is-not)

Most AI reviews stop at “this looks risky.” This skill produces a review you can audit: every finding points to a location, a contract or code path, and a severity; every gate decision is rendered from machine-readable JSON. It reads the diff, surrounding source, tests, and project rules — no build, test run, or coverage report required.

It never modifies the code under review.

## Contents

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

Copy the skill and its reviewer adapter into your project’s `.claude` directory:

```bash
git clone https://github.com/kyy-logs/code-review-skill.git
cd your-project
mkdir -p .claude/skills .claude/agents
cp -r ../code-review-skill/.claude/skills/code-review .claude/skills/
cp ../code-review-skill/.claude/agents/reviewer.md .claude/agents/
```

Claude Code discovers it as `code-review`.

### Run

Ask in Claude Code:

```text
帮我 review 这次改动
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
5. **Reconcile** — critical/high findings must be closed or explicitly rejected.
6. **Report** — render the human report’s fact sections from JSON, then verify them.
7. **Gate** — required-probe failures and open critical/high findings block the merge.

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
| `severity` | `critical` / `high` / `medium` / `low` |
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

`references/reviewer.md` is the host-neutral reviewer script. `.claude/agents/reviewer.md` is the Claude Code adapter.

The reviewer gets the frozen skill, the case inputs, and the raw probe bundle — not reference comments, expected answers, or prior reports. If the host cannot provide a fresh context, record that limitation; do not fabricate a verdict.

## What this is not

- Not a replacement for tests, CI, or human review.
- Not a guarantee that a clean report means the change is correct.
- Not a coverage tool: coverage is used when provided, not required.
- Not a fixer: it does not modify the code under review.

## Validation

<details>
<summary>11-case historical Java regression (2026-10-29)</summary>

- 11/11 cases completed; reviewer off; static review.
- Original behavior targets: 5/5 hit.
- Clean and fixed controls: 4/4 passed without false blocking.
- Two confirmed edge-case misses remain: legal input formatting in a parser, and a JSON representation round-trip in command rendering.
- 33 raw findings: 0 critical, 8 high, 20 medium, 5 low; 0 confirmed false positives, with unverified items still open.
- The full merge gate was not run.

The evaluation harness and raw reports are kept out of the published repository. This snapshot is a regression result, not a claim of general recall.

</details>

## Requirements

- Claude Code with Agent Skills support.
- Bash, Git, awk, grep, sed.
- Python 3.9+ with PyYAML (for report parsing and metrics).

## Repository layout

```text
.claude/
├── agents/reviewer.md
└── skills/code-review/
    ├── SKILL.md
    ├── assets/code-review.md
    ├── references/
    │   ├── probes.yaml
    │   ├── output-schema.md
    │   ├── reviewer.md
    │   ├── probes/
    │   └── rules/
    └── scripts/
        ├── review-mode
        ├── collect-metrics
        ├── lib-metrics
        ├── rule-grep
        └── sync-results.py
```

## Contributing

Issues and pull requests are welcome. For a behavior change, include:

- the review target (repo and base/head),
- the expected finding or gate decision,
- the observed finding or gate decision,
- the evidence that distinguishes them.

For a probe or schema change, update the probe document, the output contract, and the affected scripts together.

## License

No license has been added yet. Until one is added, the repository is all rights reserved.

If you intend to accept external contributions, add a license first — for example, MIT or Apache-2.0 — and update this section.

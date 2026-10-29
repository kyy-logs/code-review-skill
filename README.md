# code-review-skill

A standalone code-review agent skill for Claude Code. It reviews a change, records evidence-backed findings, and applies a hard merge gate.

The skill is static-review first: it reads the diff, surrounding source, tests, and rules. It does not require tests, a build, or coverage data to run, and it never modifies the code under review.

## What it does

- **Three probes**, run in registry order:
  - `test-coverage` — test quality and incremental coverage when coverage data is available.
  - `repo-guard` — rule checks plus behavioral review of the changed code.
  - `impact-analysis` — callers, public contracts, performance, and architecture impact.
- **Evidence contract** — every finding has a location, summary, evidence, and optional reproduction command. High-severity findings require a checkable contract or code path.
- **Programmatic reviewer switch** — `scripts/review-mode` reads `references/probes.yaml` and prints `run` or `skip reason=...`. When it returns `run`, dispatch the independent reviewer in a fresh context.
- **Reconciliation gate** — critical/high findings must be closed or explicitly rejected before the merge gate can pass.
- **Structured output** — probe reports and the main report use a fixed schema, so counts and gate decisions are machine-checkable.

## Requirements

- Claude Code with Agent Skills support.
- Bash, Git, awk, grep, sed.
- Python 3.9+ with PyYAML (for report parsing and metrics).

## Install

Copy the skill and the reviewer agent into your project's `.claude` directory:

```bash
git clone https://github.com/kyy-logs/code-review-skill.git
cd your-project
mkdir -p .claude/skills .claude/agents
cp -r ../code-review-skill/.claude/skills/code-review .claude/skills/
cp ../code-review-skill/.claude/agents/reviewer.md .claude/agents/
```

Claude Code discovers the skill as `code-review`.

## Use

Ask for a review in Claude Code:

```text
帮我 review 这次改动
```

or invoke the skill directly:

```text
/code-review
```

The skill supports two review modes:

- `worktree` — staged, unstaged, and untracked changes against the current `HEAD`.
- `commits` — a fixed `base..head` range.

Artifacts are written to:

```text
docs/work/active/{slug}/
├── code-review.md
└── probes/
    ├── test-coverage.md
    ├── repo-guard.md
    └── impact-analysis.md
```

## Configuration

The probe registry and reviewer policy live in `references/probes.yaml`:

```yaml
reviewer:
  mode: auto        # auto | always | never
  skip_when:
    - no_findings
    - only_docs
  policy: strict    # strict | advisory
```

Project-specific rules can be placed in `.code-review/rules/`, or pointed to with `CODE_REVIEW_RULES_DIR`. A project rule package replaces the built-in rule package rather than merging with it.

## Independent reviewer

`references/reviewer.md` is the host-neutral reviewer script. `.claude/agents/reviewer.md` is the Claude Code adapter.

The reviewer is optional. When `review-mode` returns `run`, dispatch it in a fresh context with only the case inputs, the frozen skill, and the raw probe bundle. Do not give it expected answers. If the host cannot provide an independent context, record that limitation instead of fabricating a verdict.

## Layout

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

## License

No license has been added yet. Until one is added, the repository is all rights reserved.

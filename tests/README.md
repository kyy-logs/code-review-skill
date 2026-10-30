# Offline tests

These tests exercise the review pipeline's records, three-level severity
validation, report rendering, and gate behavior. They do not call a model and
do not replace recall or reviewer evaluation.

Release-note tests run the NEWS-to-README synchronizer against temporary
documents, including stale previews, invalid markers, and repeated runs.

Installation checks copy `skills/code-review/` and the Claude adapter into a
separate temporary project and exercise the copied scripts, including paths
containing spaces. No skill-directory environment override is needed.

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

Bash-backed gate tests also need a Bash executable:

```bash
CODE_REVIEW_TEST_BASH=/usr/bin/bash python -m unittest discover -s tests -v
```

On Windows with Git Bash, point `CODE_REVIEW_TEST_BASH` at the Git Bash
executable, for example `E:/git/Git/usr/bin/bash.exe`.

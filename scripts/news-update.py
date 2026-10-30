#!/usr/bin/env python3
"""Maintain the auto-generated Unreleased block in NEWS.md from git history.

The script only replaces the marked block. Released sections and manual edits
outside the markers are preserved. Commit subjects are classified by
Conventional Commits when possible, with a small fallback for older history.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- UNRELEASED:START -->"
END = "<!-- UNRELEASED:END -->"
SECTIONS = ("Added", "Changed", "Fixed", "Removed", "Breaking Changes")

CONVENTIONAL = re.compile(
    r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$"
)
TYPE_SECTION = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "revert": "Changed",
    "style": "Changed",
}
SKIP_TYPES = {"docs", "chore", "test", "tests", "ci", "build"}
SKIP_SUBJECTS = (
    re.compile(r"^Merge\b"),
    re.compile(r"^Release\b"),
    re.compile(r"^Prepare\b.*\brelease\b", re.IGNORECASE),
    re.compile(r"^chore\(release\)"),
    re.compile(r"^docs?:\s*sync latest news", re.IGNORECASE),
)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def latest_tag(repo: Path) -> str:
    result = git(repo, "describe", "--tags", "--abbrev=0", "HEAD")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    roots = git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.splitlines()
    if not roots:
        raise ValueError("cannot find a base revision")
    return roots[-1]


def commits(repo: Path, from_rev: str, to_rev: str):
    fmt = "%s%x1f%b%x1e"
    result = git(repo, "log", "--no-merges", "--format=" + fmt, from_rev + ".." + to_rev)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git log failed")
    for record in result.stdout.split("\x1e"):
        if not record.strip():
            continue
        subject, _, body = record.partition("\x1f")
        yield subject.strip(), body


def classify(subject: str, body: str):
    if any(pattern.search(subject) for pattern in SKIP_SUBJECTS):
        return None, None
    match = CONVENTIONAL.match(subject)
    if match:
        kind = match.group("type").lower()
        if kind in SKIP_TYPES:
            return None, None
        desc = match.group("desc").strip()
        scope = match.group("scope")
        text = (scope + ": " + desc) if scope else desc
        breaking = bool(match.group("breaking")) or bool(
            re.search(r"^BREAKING[ -]CHANGE:", body, re.MULTILINE | re.IGNORECASE)
        )
        return ("Breaking Changes" if breaking else TYPE_SECTION.get(kind, "Changed")), text
    if re.match(r"^Add\b", subject):
        return "Added", subject
    if re.match(r"^Fix\b|^Resolve\b", subject):
        return "Fixed", subject
    if re.match(r"^Remove\b|^Delete\b", subject):
        return "Removed", subject
    return "Changed", subject


def unreleased_block(repo: Path, from_rev: str, to_rev: str) -> str:
    grouped = {name: [] for name in SECTIONS}
    seen = set()
    for subject, body in commits(repo, from_rev, to_rev):
        section, text = classify(subject, body)
        if not section or not text:
            continue
        key = (section, text)
        if key in seen:
            continue
        seen.add(key)
        grouped[section].append(text)

    lines = [START, "## Unreleased", ""]
    wrote = False
    for section in SECTIONS:
        if not grouped[section]:
            continue
        wrote = True
        lines.extend(["### " + section, ""])
        lines.extend("- " + item for item in grouped[section])
        lines.append("")
    if not wrote:
        lines.extend(["_No user-facing changes since the latest release._", ""])
    lines.append(END)
    return "\n".join(lines) + "\n"


def replace_block(news: str, block: str) -> str:
    if news.count(START) != 1 or news.count(END) != 1:
        raise ValueError("NEWS.md needs exactly one UNRELEASED:START / UNRELEASED:END pair.")
    start = news.index(START)
    end = news.index(END, start) + len(END)
    if start > end:
        raise ValueError("NEWS.md UNRELEASED markers are reversed.")
    tail = news[end:].lstrip("\n")
    return news[:start] + block.rstrip("\n") + "\n\n" + tail


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT, help="git repository root")
    parser.add_argument("--news", type=Path, default=None, help="NEWS.md path")
    parser.add_argument("--from", dest="from_rev", default=None, help="base revision (default: latest tag)")
    parser.add_argument("--to", dest="to_rev", default="HEAD", help="target revision")
    parser.add_argument("--check", action="store_true", help="fail if the block is stale; do not write")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    news_path = args.news.resolve() if args.news else repo / "NEWS.md"
    try:
        from_rev = args.from_rev or latest_tag(repo)
        block = unreleased_block(repo, from_rev, args.to_rev)
        before = news_path.read_text(encoding="utf-8")
        after = replace_block(before, block)
    except (OSError, ValueError) as error:
        print("news-update: " + str(error), file=sys.stderr)
        return 2

    if before == after:
        print("NEWS unreleased block is up to date.")
        return 0
    if args.check:
        print("NEWS unreleased block is stale. Run python scripts/news-update.py.", file=sys.stderr)
        return 1
    with news_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(after)
    print("Updated NEWS unreleased block from " + from_rev + ".." + args.to_rev + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())

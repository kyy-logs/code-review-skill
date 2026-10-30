#!/usr/bin/env python3
"""Copy the first NEWS release into README's marked preview; no dependencies."""

import argparse
from pathlib import Path
import re
import sys


START = "<!-- NEWS:START -->"
END = "<!-- NEWS:END -->"
ROOT = Path(__file__).resolve().parents[1]


def markdown_headings(lines):
    """Yield heading positions outside fenced code blocks."""
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not tail.strip():
                fence = None
            continue
        if fence is None:
            heading = re.match(r"^(#{2,6}) +\S", line)
            if heading:
                yield index, len(heading.group(1))


def heading_text(line):
    return re.sub(r"^#{2,6} +", "", line).strip().lower()


def preview(news):
    lines = news.splitlines()
    headings = list(markdown_headings(lines))
    releases = [index for index, level in headings if level == 2]
    released = [index for index in releases if heading_text(lines[index]) not in ("unreleased", "未发布")]
    if not released:
        raise ValueError("NEWS.md needs a released version heading starting with '## '.")
    start = released[0]
    end = next((index for index in releases if index > start), len(lines))
    if not "\n".join(lines[start + 1:end]).strip():
        raise ValueError("The latest NEWS release has no content.")
    for index, level in headings:
        if start <= index < end and level < 6:
            lines[index] = "#" + lines[index]
    return "\n".join(lines[start:end]).strip() + "\n\n[Full update history](NEWS.md)"


def synchronize(readme, news):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README.md needs exactly one NEWS:START / NEWS:END pair.")
    start = readme.index(START) + len(START)
    end = readme.index(END)
    if start > end:
        raise ValueError("README.md NEWS markers are reversed.")
    newline = "\r\n" if "\r\n" in readme else "\n"
    content = preview(news).replace("\n", newline)
    return readme[:start] + newline + content + newline + readme[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--news", type=Path, default=ROOT / "NEWS.md")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--check", action="store_true", help="Fail if the preview is stale; do not write.")
    args = parser.parse_args()
    try:
        before = args.readme.read_bytes()
        after = synchronize(before.decode("utf-8"), args.news.read_text(encoding="utf-8")).encode("utf-8")
        if before == after:
            print("README news preview is up to date.")
            return 0
        if args.check:
            print("README news preview is stale. Run python scripts/sync-news.py.", file=sys.stderr)
            return 1
        args.readme.write_bytes(after)
        print("Updated README news preview.")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"sync-news: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

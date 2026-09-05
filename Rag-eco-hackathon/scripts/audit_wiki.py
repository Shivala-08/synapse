#!/usr/bin/env python3
"""Audit the Second Brain vault without modifying anything.

Checks:
  - _master-index.md exists
  - every topic folder has an _index.md
  - every article ends with a "## Key Takeaways" section
  - no article is empty
  - every [[wikilink]] resolves to an existing note or topic folder

Link resolution follows Obsidian conventions:
  - a target resolves if any note has that name (basename without extension)
  - a target resolves if it names a topic folder (folder-note convention)
  - links inside fenced code blocks or inline code spans are ignored

Exits 0 when the vault is healthy, 1 when hard problems (broken links,
missing indexes, empty articles) are found. Prints a full report either way.

Usage:
    python scripts/audit_wiki.py [path-to-wiki]
    (default: the second_brain domain source path from the domain profile)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_domain_profile  # noqa: E402

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
INDEX_FILES = {"_index.md", "_master-index.md"}


def collect_notes(wiki: Path) -> tuple[dict[str, Path], set[str]]:
    """Return (notes by lowercase stem, topic folder names)."""
    notes: dict[str, Path] = {}
    for f in wiki.rglob("*.md"):
        if f.name.startswith("."):
            continue
        notes[f.stem.lower()] = f
    topics = {d.name.lower() for d in wiki.iterdir() if d.is_dir() and any(d.glob("*.md"))}
    return notes, topics


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans before link checking."""
    text = FENCE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    return text


def audit(wiki: Path) -> tuple[list[str], list[str]]:
    """Return (problems, notes). Problems are human-readable violations."""
    problems: list[str] = []
    notes: list[str] = []

    master = wiki / "_master-index.md"
    if not master.exists():
        problems.append("missing _master-index.md")

    notes_map, topics = collect_notes(wiki)

    # Topic folders (directories containing markdown, excluding wiki root)
    topic_dirs = sorted(d for d in wiki.iterdir() if d.is_dir() and any(d.glob("*.md")))

    for topic in topic_dirs:
        if not (topic / "_index.md").exists():
            problems.append(f"missing _index.md in {topic.name}/")

    def resolvable(target: str) -> bool:
        key = target.strip().lower()
        return key in notes_map or key in topics

    # Walk EVERY markdown file (articles, topic indexes, master index) and
    # check its links. Only non-index articles require content + Key Takeaways.
    for f in sorted(wiki.rglob("*.md")):
        if f.name.startswith("."):
            continue
        rel = f.relative_to(wiki)
        text = f.read_text(encoding="utf-8", errors="ignore")

        if f.name in INDEX_FILES:
            if not text.strip():
                problems.append(f"empty index: {rel}")
        else:
            notes.append(f.name)
            if not text.strip():
                problems.append(f"empty article: {rel}")
            if "## Key Takeaways" not in text:
                problems.append(f"missing '## Key Takeaways': {rel}")

        for m in WIKILINK_RE.finditer(strip_code(text)):
            target = m.group(1).strip()
            if not resolvable(target):
                problems.append(f"broken wikilink [[{target}]] in {rel}")

    return problems, notes


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg:
        wiki = Path(arg).resolve()
    else:
        dp = load_domain_profile("second_brain")
        wiki = Path(dp.source_path).resolve()
        if not wiki.exists():
            print(f"ERROR: source path does not exist: {wiki}")
            print("       Pass the wiki path explicitly: python scripts/audit_wiki.py <path>")
            return 2

    if not wiki.exists():
        print(f"ERROR: no such directory: {wiki}")
        return 2

    problems, notes = audit(wiki)

    print(f"Vault: {wiki}")
    print(f"Articles found: {len(notes)}")
    print()

    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  ✗ {p}")
        print()
        print("STATUS: FAIL")
        return 1

    print("No problems found.")
    print()
    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
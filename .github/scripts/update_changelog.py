#!/usr/bin/env python3
"""
Promote the "[Unreleased]" section of CHANGELOG.md to a dated version section
whenever a new GitHub release is published, leaving a fresh, empty
"[Unreleased]" section at the top for future changes.

Reads its input from environment variables (set by the calling GitHub Actions
workflow):
    RELEASE_TAG  - the tag of the published release, e.g. "v1.2.3"
    RELEASE_DATE - the publish date, formatted as YYYY-MM-DD
    RELEASE_BODY - the release notes body (used as a fallback when the
                   "[Unreleased]" section has no entries yet)
"""
import os
import re
import sys

CHANGELOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "CHANGELOG.md")

UNRELEASED_HEADING = "## [Unreleased]"
NEXT_HEADING_RE = re.compile(r"^## \[", re.MULTILINE)
FALLBACK_NOTE = "_No documented changes._"


def promote_unreleased(content: str, version: str, date: str, release_body: str) -> str:
    """
    Move the contents of the "[Unreleased]" section into a new, dated version
    section directly below it, and reset "[Unreleased]" to be empty.
    """
    unreleased_start = content.find(UNRELEASED_HEADING)
    if unreleased_start == -1:
        raise ValueError('Could not find an "## [Unreleased]" section in CHANGELOG.md')

    body_start = unreleased_start + len(UNRELEASED_HEADING)

    next_heading_match = NEXT_HEADING_RE.search(content, body_start)
    body_end = next_heading_match.start() if next_heading_match else len(content)

    unreleased_body = content[body_start:body_end].strip("\n")

    if not unreleased_body:
        unreleased_body = release_body.strip() if release_body.strip() else FALLBACK_NOTE

    new_section = (
        f"{UNRELEASED_HEADING}\n\n"
        f"## [{version}] - {date}\n\n"
        f"{unreleased_body}\n\n"
    )

    return content[:unreleased_start] + new_section + content[body_end:]


def main() -> int:
    """
    Entry point: read release metadata from the environment and update
    CHANGELOG.md accordingly.
    """
    tag = os.environ.get("RELEASE_TAG", "").strip()
    date = os.environ.get("RELEASE_DATE", "").strip()
    release_body = os.environ.get("RELEASE_BODY", "")

    if not tag or not date:
        print("RELEASE_TAG and RELEASE_DATE environment variables are required.", file=sys.stderr)
        return 1

    version = tag[1:] if tag.lower().startswith("v") else tag

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if f"## [{version}]" in content:
        print(f"CHANGELOG.md already has an entry for version {version}, nothing to do.")
        return 0

    updated = promote_unreleased(content, version, date, release_body)

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"Promoted [Unreleased] to [{version}] - {date} in CHANGELOG.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

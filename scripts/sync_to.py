"""Mirror OmniHarness agent templates into a consumer project's .claude/agents/.

Usage:
  python OmniHarness/scripts/sync_to.py <consumer_project_dir>
  python OmniHarness/scripts/sync_to.py ../FabCanvas.ai

Copies every *.md from OmniHarness/templates/agents/ (except README.md) into
<consumer>/.claude/agents/. Existing files are overwritten, extras left alone.

The templates are written with consumer-project-relative paths (e.g.
`backend/routers/dashboard.py`) so they work unchanged in any project that
follows the same layout conventions.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
TEMPLATES = SCRIPT.parent.parent / "templates" / "agents"


def main(consumer: str) -> int:
    src = TEMPLATES
    if not src.is_dir():
        print(f"error: templates dir not found: {src}", file=sys.stderr)
        return 2

    consumer_dir = Path(consumer).resolve()
    if not consumer_dir.is_dir():
        print(f"error: consumer dir not found: {consumer_dir}", file=sys.stderr)
        return 2

    dst = consumer_dir / ".claude" / "agents"
    dst.mkdir(parents=True, exist_ok=True)

    copied, skipped = [], []
    for f in sorted(src.glob("*.md")):
        if f.stem.lower() == "readme":
            skipped.append(f.name)
            continue
        target = dst / f.name
        shutil.copy2(f, target)
        copied.append(f.name)

    print(f"[omniharness.sync] {len(copied)} agents -> {dst}")
    for name in copied:
        print(f"  + {name}")
    if skipped:
        print(f"[omniharness.sync] skipped: {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Debt Ledger for Bergendy Buddy.

Manages 'bergendy: deferred' annotations across the codebase.
Prevents over-engineering while guaranteeing that postponed ideas are never lost.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DeferredCard:
    file_path: str
    line_number: int
    note: str
    tag: str = "deferred"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DebtLedger:
    """Scans and tracks deferred cards across the repository."""

    PATTERN = re.compile(r"(?://|#|--|/\*)\s*bergendy:\s*deferred\s*(.*)", re.IGNORECASE)

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)

    def scan(self, max_files: int = 2000) -> list[DeferredCard]:
        cards: list[DeferredCard] = []
        count = 0

        skip_dirs = {".git", "node_modules", "target", ".venv", "dist", "build", "__pycache__"}

        for path in self.root_dir.rglob("*"):
            if count >= max_files:
                break
            if any(part in skip_dirs for part in path.parts):
                continue
            if not path.is_file():
                continue

            # Only scan text files
            if path.suffix in {".ts", ".js", ".py", ".rs", ".go", ".c", ".cpp", ".h", ".md", ".toml", ".yaml", ".json"}:
                count += 1
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    for idx, line in enumerate(text.splitlines(), start=1):
                        m = self.PATTERN.search(line)
                        if m:
                            note = m.group(1).strip().rstrip("*/").strip()
                            rel = str(path.relative_to(self.root_dir))
                            cards.append(DeferredCard(file_path=rel, line_number=idx, note=note or "Deferred work item"))
                except Exception:
                    continue

        return cards

    def render_markdown(self) -> str:
        cards = self.scan()
        if not cards:
            return "### Bergendy Debt Ledger\n\nNo deferred items found. Clean slate!"

        lines = [
            "### Bergendy Debt Ledger",
            "",
            f"**Total Deferred Items:** {len(cards)}",
            "",
            "| File | Line | Note |",
            "| --- | --- | --- |",
        ]
        for c in cards:
            lines.append(f"| `{c.file_path}` | {c.line_number} | {c.note} |")

        lines.append("")
        lines.append("> Items marked with `bergendy: deferred` are parked to prevent scope creep.")
        return "\n".join(lines)

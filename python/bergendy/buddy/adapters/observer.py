# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Git & Filesystem Observer for Bergendy Buddy.

Monitors working directory modifications in real-time when agent hooks are not
directly wired into the IDE, detecting file edits, diffs, and test runs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class RepoObserver:
    """Watches git repository working tree for edits and diffs."""

    def __init__(self, session: Any, repo_path: str = "."):
        self.session = session
        self.repo_path = Path(repo_path).resolve()
        self._last_snapshot: dict[str, float] = {}

    def capture_status(self) -> dict[str, str]:
        """Returns dict of relative_file_path -> git status (M, A, D, etc)."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            files = {}
            for line in res.stdout.splitlines():
                if len(line) >= 4:
                    status = line[:2].strip()
                    file_path = line[3:].strip()
                    files[file_path] = status
            return files
        except Exception:
            return {}

    def get_file_diff(self, file_path: str) -> str:
        """Returns git diff for specific file."""
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD", "--", file_path],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout
        except Exception:
            return ""

    def poll_once(self) -> list[dict[str, Any]]:
        """Checks for any newly modified files and emits FileEdit events to the session."""
        current_status = self.capture_status()
        reactions = []

        for file_path, status in current_status.items():
            full_path = self.repo_path / file_path
            if not full_path.exists() or not full_path.is_file():
                continue

            mtime = full_path.stat().st_mtime
            last_mtime = self._last_snapshot.get(file_path, 0.0)

            if mtime > last_mtime:
                self._last_snapshot[file_path] = mtime
                diff = self.get_file_diff(file_path)
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    content = ""

                lines = content.splitlines()
                event = {
                    "type": "FileEdit",
                    "payload": {
                        "path": file_path,
                        "diff": diff or None,
                        "lines_added": len(lines),
                        "lines_removed": 0,
                        "new_content": content,
                    },
                }
                raw = self.session.handle_event(json.dumps(event))
                reactions.append(json.loads(raw))

        return reactions

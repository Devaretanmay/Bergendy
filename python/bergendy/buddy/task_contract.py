# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Task Contract and Change Budget for Bergendy Engineering Buddy.

Translates user instructions and constraints into a bounded contract that the
restraint and completion engines enforce against coding agents.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ChangeBudget:
    """Ponytail change budget constraining agent scope."""

    max_files: int = 4
    max_dependencies: int = 0
    max_abstractions: int = 1
    max_lines_added: int = 300
    allowed_paths: list[str] = field(default_factory=list)
    banned_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeBudget:
        return cls(
            max_files=data.get("max_files", 4),
            max_dependencies=data.get("max_dependencies", 0),
            max_abstractions=data.get("max_abstractions", 1),
            max_lines_added=data.get("max_lines_added", 300),
            allowed_paths=data.get("allowed_paths", []),
            banned_patterns=data.get("banned_patterns", []),
        )


@dataclass
class TaskContract:
    """Contract binding an AI coding session."""

    task_id: str
    prompt: str
    budget: ChangeBudget = field(default_factory=ChangeBudget)
    verify_commands: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "budget": self.budget.to_dict(),
            "verify_commands": self.verify_commands,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskContract:
        budget_data = data.get("budget", {})
        budget = ChangeBudget.from_dict(budget_data) if isinstance(budget_data, dict) else ChangeBudget()
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())[:8]),
            prompt=data.get("prompt", ""),
            budget=budget,
            verify_commands=data.get("verify_commands", []),
            created_at=data.get("created_at", time.time()),
        )

    @classmethod
    def from_prompt(
        cls,
        prompt: str,
        repo_path: str = ".",
        task_id: Optional[str] = None,
        max_files: Optional[int] = None,
        verify_cmd: Optional[str] = None,
    ) -> TaskContract:
        """Infer budget and constraints directly from the user's prompt."""
        tid = task_id or f"task-{uuid.uuid4().hex[:8]}"
        lower = prompt.lower()

        # Sensible defaults based on task intent
        if "fix" in lower or "bug" in lower or "typo" in lower or "patch" in lower:
            budget = ChangeBudget(
                max_files=max_files or 3,
                max_dependencies=0,
                max_abstractions=0,
                max_lines_added=150,
            )
        elif "refactor" in lower or "clean" in lower or "simplify" in lower:
            budget = ChangeBudget(
                max_files=max_files or 8,
                max_dependencies=0,
                max_abstractions=0,
                max_lines_added=250,
            )
        else:
            budget = ChangeBudget(
                max_files=max_files or 5,
                max_dependencies=0,
                max_abstractions=1,
                max_lines_added=400,
            )

        verify_cmds = [verify_cmd] if verify_cmd else []
        return cls(task_id=tid, prompt=prompt, budget=budget, verify_commands=verify_cmds)

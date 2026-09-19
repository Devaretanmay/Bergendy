# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Bergendy Buddy: AI Coding Guardian & Companion Subsystem."""

from __future__ import annotations

import json
from typing import Any, Optional

try:
    from bergendy._core import BuddySession, buddy_validate_pet_manifest, buddy_validate_pet_manifest_file
except ImportError:
    BuddySession = None  # type: ignore
    buddy_validate_pet_manifest = None  # type: ignore
    buddy_validate_pet_manifest_file = None  # type: ignore

from .adapters.cursor import CursorHookHandler
from .adapters.observer import RepoObserver
from .deferred import DebtLedger, DeferredCard
from .proof import ProofEngine, TestExecution
from .task_contract import ChangeBudget, TaskContract


class Buddy:
    """The AI Coding Guardian & Engineering Companion.

    Watches AI coding sessions, enforcing Ponytail simplicity,
    preventing test-gaming, and guiding the on-screen pet companion.
    """

    def __init__(
        self,
        contract: Optional[TaskContract] = None,
        repo_path: str = ".",
    ):
        self.repo_path = repo_path
        self.contract = contract or TaskContract.from_prompt("General assistance", repo_path=repo_path)
        budget_json = self.contract.budget.to_json()

        if BuddySession is not None:
            self._session = BuddySession(self.contract.task_id, self.repo_path, budget_json)
        else:
            self._session = None

        self.proof = ProofEngine()
        self.deferred = DebtLedger(self.repo_path)
        self.cursor = CursorHookHandler(self._session) if self._session else None
        self.observer = RepoObserver(self._session, self.repo_path) if self._session else None

    def handle_event(self, event: dict[str, Any] | str) -> dict[str, Any]:
        """Dispatch any AgentEvent to the guardian session."""
        if self._session is None:
            return {"speech_bubble": "Buddy session not available", "is_blocked": False}

        event_str = json.dumps(event) if isinstance(event, dict) else event
        raw = self._session.handle_event(event_str)
        return json.loads(raw)

    def record_edit(
        self,
        file_path: str,
        diff: Optional[str] = None,
        new_content: Optional[str] = None,
        lines_added: int = 0,
        lines_removed: int = 0,
    ) -> dict[str, Any]:
        """Record an edit made to a file."""
        return self.handle_event({
            "type": "FileEdit",
            "payload": {
                "path": file_path,
                "diff": diff,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "new_content": new_content,
            },
        })

    def verify(self, command: Optional[str] = None) -> TestExecution:
        """Run verification tests and submit evidence to the guardian."""
        cmd = command
        if not cmd and self.contract.verify_commands:
            cmd = self.contract.verify_commands[0]
        if not cmd:
            cmd = "pytest"

        execution = self.proof.run(cmd, cwd=self.repo_path)

        # Notify session of test execution
        self.handle_event({
            "type": "TestRun",
            "payload": {
                "command": execution.command,
                "passed_count": execution.passed_count,
                "failed_count": execution.failed_count,
                "exit_code": execution.exit_code,
                "duration_ms": execution.duration_ms,
            },
        })

        return execution

    def claim_done(self, summary: str = "") -> dict[str, Any]:
        """Challenge the agent's claim of task completion."""
        return self.handle_event({
            "type": "AgentClaimDone",
            "payload": {
                "summary": summary,
            },
        })

    def state_summary(self) -> dict[str, Any]:
        if self._session is None:
            return {}
        return json.loads(self._session.state_summary())

    @property
    def pet_state(self) -> str:
        return self._session.get_pet_state() if self._session else "watching"

    @property
    def active_bubble(self) -> str:
        return self._session.get_active_bubble() if self._session else ""


__all__ = [
    "Buddy",
    "TaskContract",
    "ChangeBudget",
    "CursorHookHandler",
    "RepoObserver",
    "ProofEngine",
    "TestExecution",
    "DebtLedger",
    "DeferredCard",
]

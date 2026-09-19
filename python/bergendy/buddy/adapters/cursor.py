# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Cursor Hook Adapter for Bergendy Buddy.

Binds to Cursor agent lifecycle hooks:
- preToolUse / postToolUse
- beforeShellExecution
- afterFileEdit
- stop (agent completion claim)

Translates each hook into an AgentEvent and passes it to the Rust buddy session.
Enforces Level 4 Blocks and Level 2/3 Nudges/Challenges.
"""

from __future__ import annotations

import json
from typing import Any, Optional

try:
    from bergendy._core import BuddySession
except ImportError:
    BuddySession = None  # type: ignore


class CursorHookHandler:
    """Handles Cursor agent hooks and translates them to Buddy reactions."""

    def __init__(self, session: Any):
        self.session = session

    def on_pre_tool_use(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        event = {
            "type": "ToolCall",
            "payload": {
                "tool_name": tool_name,
                "arguments": arguments,
                "is_pre": True,
            },
        }
        reaction = self._dispatch(event)
        return self._format_cursor_response(reaction)

    def on_post_tool_use(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        event = {
            "type": "ToolCall",
            "payload": {
                "tool_name": tool_name,
                "arguments": arguments,
                "is_pre": False,
            },
        }
        reaction = self._dispatch(event)
        return self._format_cursor_response(reaction)

    def on_before_shell_execution(self, command: str) -> dict[str, Any]:
        event = {
            "type": "ToolCall",
            "payload": {
                "tool_name": "bash",
                "arguments": {"command": command},
                "is_pre": True,
            },
        }
        reaction = self._dispatch(event)
        return self._format_cursor_response(reaction)

    def on_after_file_edit(
        self,
        path: str,
        diff: Optional[str] = None,
        lines_added: int = 0,
        lines_removed: int = 0,
        new_content: Optional[str] = None,
    ) -> dict[str, Any]:
        event = {
            "type": "FileEdit",
            "payload": {
                "path": path,
                "diff": diff,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "new_content": new_content,
            },
        }
        reaction = self._dispatch(event)
        return self._format_cursor_response(reaction)

    def on_stop(self, summary: str = "") -> dict[str, Any]:
        """Called when agent declares it has finished the task."""
        event = {
            "type": "AgentClaimDone",
            "payload": {
                "summary": summary,
            },
        }
        reaction = self._dispatch(event)
        return self._format_cursor_response(reaction)

    def _dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        raw_res = self.session.handle_event(json.dumps(event))
        return json.loads(raw_res)

    def _format_cursor_response(self, reaction: dict[str, Any]) -> dict[str, Any]:
        is_blocked = reaction.get("is_blocked", False)
        speech = reaction.get("speech_bubble", "")
        level = reaction.get("level", "Level0Silent")
        evidence = reaction.get("evidence")

        if is_blocked:
            return {
                "proceed": False,
                "action": "block",
                "reason": speech,
                "evidence": evidence,
                "pet_state": reaction.get("pet_state"),
            }

        if level in ("Level2Nudge", "Level3Challenge"):
            return {
                "proceed": True,
                "action": "challenge" if level == "Level3Challenge" else "nudge",
                "message": speech,
                "evidence": evidence,
                "pet_state": reaction.get("pet_state"),
            }

        return {
            "proceed": True,
            "action": "allow",
            "speech": speech,
            "pet_state": reaction.get("pet_state"),
        }

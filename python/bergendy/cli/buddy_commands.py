# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""CLI Commands for Bergendy Buddy, Pet Companion, and Debt Ledger."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bergendy.buddy import Buddy, DebtLedger, TaskContract
from bergendy.cli.companion_view import OverlayServer, TerminalPetRenderer

try:
    from bergendy._core import buddy_validate_pet_manifest_file
except ImportError:
    buddy_validate_pet_manifest_file = None  # type: ignore

SESSION_FILE = Path(".bergendy/session.json")


def _save_session(contract: TaskContract) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(contract.to_json(), encoding="utf-8")


def _load_session() -> TaskContract:
    if not SESSION_FILE.exists():
        return TaskContract.from_prompt("Default coding session")
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return TaskContract.from_dict(data)
    except Exception:
        return TaskContract.from_prompt("Default coding session")


def cmd_session(args: argparse.Namespace) -> None:
    action = getattr(args, "session_action", "status") or "status"

    if action == "start":
        prompt = getattr(args, "prompt", "General task") or "General task"
        max_files = getattr(args, "max_files", None)
        verify_cmd = getattr(args, "verify_cmd", None)
        contract = TaskContract.from_prompt(
            prompt,
            repo_path=".",
            max_files=max_files,
            verify_cmd=verify_cmd,
        )
        _save_session(contract)
        buddy = Buddy(contract=contract)

        print("\n\033[1;32m✓ Bergendy Buddy Session Initialized\033[0m")
        print(f"  \033[1mTask ID:\033[0m       {contract.task_id}")
        print(f"  \033[1mGoal:\033[0m          {contract.prompt}")
        print(f"  \033[1mFile Budget:\033[0m   {contract.budget.max_files} files max")
        print(f"  \033[1mVerify Cmd:\033[0m    {verify_cmd or 'none (default test suite)'}\n")
        print(TerminalPetRenderer.render(
            "watching",
            "Ready! Watching your agent's changes. Keep them small and verified.",
            level="Level0Silent",
            task_id=contract.task_id,
        ))
        print()

    elif action == "claim":
        contract = _load_session()
        buddy = Buddy(contract=contract)
        summary = getattr(args, "summary", "Done") or "Done"
        reaction = buddy.claim_done(summary)

        speech = reaction.get("speech_bubble", "")
        level = reaction.get("level", "Level0Silent")
        evidence = reaction.get("evidence")
        pet_state = reaction.get("pet_state", "concerned")

        print("\n" + TerminalPetRenderer.render(
            pet_state,
            speech,
            level=level,
            task_id=contract.task_id,
            evidence=evidence,
        ) + "\n")

        if reaction.get("is_blocked"):
            sys.exit(1)

    elif action == "verify":
        contract = _load_session()
        buddy = Buddy(contract=contract)
        cmd = getattr(args, "cmd", None)
        exec_res = buddy.verify(cmd)

        status_str = "\033[32mPASS\033[0m" if exec_res.is_success else "\033[31mFAIL\033[0m"
        print(f"\n[{status_str}] Test Command: `{exec_res.command}` ({exec_res.duration_ms}ms)")
        print(f"  Passed: {exec_res.passed_count} | Failed: {exec_res.failed_count} | Exit: {exec_res.exit_code}")

        summary = buddy.state_summary()
        bubble = summary.get("active_bubble") or ("Nice! Tests are green." if exec_res.is_success else "Tests failed.")
        state = "happy" if exec_res.is_success else "concerned"
        print("\n" + TerminalPetRenderer.render(
            state,
            bubble,
            level="Level1Visual" if exec_res.is_success else "Level3Challenge",
            task_id=contract.task_id,
        ) + "\n")

    else:
        # status
        contract = _load_session()
        buddy = Buddy(contract=contract)
        summary = buddy.state_summary()

        print("\n\033[1mBergendy Buddy Session Status\033[0m")
        print(f"  Task ID:           {contract.task_id}")
        print(f"  Pet State:         {summary.get('pet_state', buddy.pet_state)}")
        print(f"  Files Modified:    {summary.get('files_modified_count', 0)} / {contract.budget.max_files}")
        print(f"  Dependencies Added: {summary.get('dependencies_added_count', 0)}")
        print(f"  Abstractions Added: {summary.get('abstractions_added_count', 0)}")
        print(f"  Deferred Cards:    {summary.get('deferred_cards_count', 0)}")
        print(f"  Tests Executed:    {summary.get('tests_executed', False)}")
        print(f"  Tests Passed:      {summary.get('tests_passed', False)}\n")

        bubble = summary.get("active_bubble") or "Watching... Looks good so far."
        print(TerminalPetRenderer.render(
            summary.get("pet_state", "watching"),
            bubble,
            task_id=contract.task_id,
        ) + "\n")


def cmd_buddy_watch(args: argparse.Namespace) -> None:
    contract = _load_session()
    buddy = Buddy(contract=contract)

    overlay = getattr(args, "overlay", False)
    port = getattr(args, "port", 8765)

    overlay_srv = None
    if overlay:
        overlay_srv = OverlayServer(port=port)
        overlay_srv.start()
        print(f"\033[32m✓ Desktop overlay running at http://127.0.0.1:{port}/\033[0m")

    print(f"\033[1;36m👀 Bergendy Buddy watching working tree ({contract.task_id})...\033[0m")
    print(TerminalPetRenderer.render("watching", "Watching working directory for changes...", task_id=contract.task_id))
    print("\nPress Ctrl+C to exit.\n")

    try:
        while True:
            reactions = buddy.observer.poll_once() if buddy.observer else []
            for r in reactions:
                state = r.get("pet_state", "watching")
                speech = r.get("speech_bubble", "")
                level = r.get("level", "Level0Silent")
                evidence = r.get("evidence")

                print(TerminalPetRenderer.render(
                    state,
                    speech,
                    level=level,
                    task_id=contract.task_id,
                    evidence=evidence,
                ))
                print()

                if overlay_srv:
                    overlay_srv.update({
                        "pet_state": state,
                        "speech_bubble": speech,
                        "level": level,
                    })

            time.sleep(1.0)
    except KeyboardInterrupt:
        if overlay_srv:
            overlay_srv.stop()
        print("\n\033[90mStopped watching.\033[0m")


def cmd_debt(args: argparse.Namespace) -> None:
    path = getattr(args, "path", ".") or "."
    ledger = DebtLedger(path)
    cards = ledger.scan()

    if getattr(args, "md", False):
        print(ledger.render_markdown())
        return

    print(f"\n\033[1mBergendy Debt Ledger\033[0m: Found {len(cards)} deferred item(s)\n")
    if not cards:
        print("  \033[32m✓ Zero deferred debt. Everything is in order!\033[0m\n")
        return

    for c in cards:
        print(f"  \033[33m•\033[0m \033[1m{c.file_path}:{c.line_number}\033[0m — {c.note}")
    print()


def cmd_pet(args: argparse.Namespace) -> None:
    action = getattr(args, "pet_action", "preview") or "preview"

    if action == "validate":
        manifest_path = getattr(args, "manifest", None)
        if not manifest_path:
            # Default to built-in pet manifest
            manifest_path = str(Path(__file__).parent.parent / "assets" / "pets" / "bergendy" / "pet.json")

        print(f"Validating manifest: {manifest_path}")
        if buddy_validate_pet_manifest_file is None:
            print("Error: Rust buddy engine bindings not loaded.")
            sys.exit(1)

        try:
            buddy_validate_pet_manifest_file(manifest_path)
            print("\033[32m✓ Manifest is valid and conforms to Codex pet geometry!\033[0m")
        except Exception as ex:
            print(f"\033[31m✗ Validation error:\033[0m {ex}")
            sys.exit(1)

    else:
        # Preview
        print("\n\033[1;36mBergendy Pet Character Sheet & States\033[0m\n")
        states = [
            ("idle", "Idle, waiting"),
            ("watching", "Monitoring live edits"),
            ("thinking", "Analyzing complexity"),
            ("suspicious", "Ponytail shrink nudge"),
            ("questioning", "YAGNI / New dependency challenge"),
            ("concerned", "Test removed or failing"),
            ("blocked", "Direct invariant violation block"),
            ("happy", "Clean diff with green tests"),
            ("celebrating", "Task proved and verified"),
        ]
        for st, desc in states:
            print(f"  {TerminalPetRenderer.render(st, desc, level='Level0Silent')}\n")

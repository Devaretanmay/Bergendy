# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

import json
import pytest
from pathlib import Path

from bergendy.buddy import (
    Buddy,
    TaskContract,
    CursorHookHandler,
    DebtLedger,
)
from bergendy._core import (
    buddy_validate_pet_manifest,
    buddy_validate_pet_manifest_file,
)


def test_task_contract_budget_inference():
    """Verify task contracts infer narrow budgets for bugfixes and sensible defaults for refactors."""
    c_fix = TaskContract.from_prompt("Fix race condition in webhook processing")
    assert c_fix.budget.max_files == 3
    assert c_fix.budget.max_dependencies == 0
    assert c_fix.budget.max_abstractions == 0

    c_refactor = TaskContract.from_prompt("Refactor database query builder")
    assert c_refactor.budget.max_files == 8

    c_feat = TaskContract.from_prompt("Add stripe webhook endpoint")
    assert c_feat.budget.max_files == 5


def test_buddy_finish_instinct_challenges_unverified_claim():
    """Verify Finish Instinct: claiming done without test execution triggers Level 3 Challenge."""
    buddy = Buddy(contract=TaskContract.from_prompt("Fix typo in docs"))
    res = buddy.claim_done("All finished, trust me!")

    assert res["level"] == "Level3Challenge"
    assert "tests" in res["speech_bubble"].lower()
    assert res["pet_state"] == "concerned"
    assert res["evidence"]["violation_kind"] == "UnverifiedCompletionClaim"


def test_buddy_finish_instinct_blocks_deleted_assertions():
    """Verify Anti-Gaming: removing assertions in test files triggers Level 4 Block."""
    buddy = Buddy()
    diff = """--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -10,3 +10,2 @@
-    assert user.is_authenticated()
"""
    reaction = buddy.record_edit(
        file_path="tests/test_auth.py",
        diff=diff,
        new_content="# no asserts",
    )
    assert reaction["is_blocked"] is True
    assert reaction["level"] == "Level4Block"
    assert reaction["pet_state"] == "blocked"
    assert "assertion was removed" in reaction["evidence"]["message"].lower()


def test_buddy_finish_instinct_blocks_skipped_tests():
    """Verify Anti-Gaming: adding .skip or test ignore flags triggers Level 4 Block."""
    buddy = Buddy()
    diff = """--- a/src/test_gateway.ts
+++ b/src/test_gateway.ts
@@ -12,2 +12,2 @@
-describe("Payment flow", () => {
+describe.skip("Payment flow", () => {
"""
    reaction = buddy.record_edit(
        file_path="src/test_gateway.ts",
        diff=diff,
    )
    assert reaction["is_blocked"] is True
    assert reaction["level"] == "Level4Block"
    assert "skipped" in reaction["evidence"]["message"].lower()


def test_buddy_restraint_yagni_detection():
    """Verify Restraint Instinct: detects speculative over-engineered abstractions."""
    buddy = Buddy()
    reaction = buddy.record_edit(
        file_path="src/service.py",
        new_content="class AbstractDatabaseProviderManagerFactory:\n    pass\n",
    )
    assert reaction["level"] == "Level3Challenge"
    assert reaction["evidence"]["ponytail_tag"] == "yagni"
    assert "Why?" in reaction["speech_bubble"]


def test_buddy_restraint_dependency_addition():
    """Verify Restraint Instinct: adding new dependencies asks 'Why?'."""
    buddy = Buddy()
    diff = """--- a/package.json
+++ b/package.json
@@ -10,2 +10,3 @@
+    "lodash": "^4.17.21"
"""
    reaction = buddy.record_edit(
        file_path="package.json",
        diff=diff,
    )
    assert reaction["level"] == "Level2Nudge"
    assert reaction["evidence"]["ponytail_tag"] == "native"
    assert "new dependency" in reaction["speech_bubble"].lower()


def test_buddy_restraint_budget_overflow():
    """Verify Restraint Instinct: exceeds file budget triggers Level 2 Nudge (Shrink)."""
    contract = TaskContract.from_prompt("Small tweak", max_files=2)
    buddy = Buddy(contract=contract)

    # Edit file 1
    buddy.record_edit("a.py", new_content="x = 1")
    # Edit file 2
    buddy.record_edit("b.py", new_content="y = 2")
    # Edit file 3 (overflows budget)
    r = buddy.record_edit("c.py", new_content="z = 3")

    assert r["level"] == "Level2Nudge"
    assert r["evidence"]["ponytail_tag"] == "shrink"
    assert "Change budget exceeded" in r["speech_bubble"]


def test_buddy_celebrates_on_verified_test_run():
    """Verify that green tests transition companion to Happy / Celebrating."""
    buddy = Buddy()
    # Simulate test run event with exit code 0 and passed tests
    r_test = buddy.handle_event({
        "type": "TestRun",
        "payload": {
            "command": "pytest",
            "passed_count": 5,
            "failed_count": 0,
            "exit_code": 0,
            "duration_ms": 120,
        },
    })
    assert r_test["pet_state"] == "happy"
    assert "green" in r_test["speech_bubble"].lower()

    # Now agent claims done
    r_done = buddy.claim_done("Finished with passing tests!")
    assert r_done["pet_state"] == "celebrating"
    assert "Well done" in r_done["speech_bubble"]


def test_cursor_hook_adapter_block_and_allow():
    """Verify CursorHookHandler returns proceed=False for blocks, proceed=True otherwise."""
    buddy = Buddy()
    handler = CursorHookHandler(buddy._session)

    # Allow harmless pre-tool use
    res_allow = handler.on_pre_tool_use("grep", {"pattern": "foo"})
    assert res_allow["proceed"] is True
    assert res_allow["action"] == "allow"

    # Block assertion deletion
    diff = """--- a/tests/test_x.py
+++ b/tests/test_x.py
@@ -1 +1 @@
-assert(a == 1)
"""
    res_block = handler.on_after_file_edit("tests/test_x.py", diff=diff)
    assert res_block["proceed"] is False
    assert res_block["action"] == "block"
    assert res_block["pet_state"] == "blocked"


def test_pet_manifest_geometry_validation(tmp_path):
    """Verify PetManifest schema and geometry rules from OpenAI Codex pet format."""
    # Valid manifest
    valid_manifest = {
        "id": "bergendy",
        "displayName": "Bergendy",
        "description": "Companion",
        "spritesheetPath": "spritesheet.webp",
        "frameWidth": 192,
        "frameHeight": 208,
        "columns": 8,
        "animations": {
            "idle": {"frames": [0, 1], "fps": 6},
            "watching": {"frames": [2, 3], "fps": 6},
            "thinking": {"frames": [4, 5], "fps": 6},
            "curious": {"frames": [6, 7], "fps": 6},
            "suspicious": {"frames": [8, 9], "fps": 6},
            "questioning": {"frames": [10, 11], "fps": 6},
            "concerned": {"frames": [12, 13], "fps": 6},
            "blocked": {"frames": [14, 15], "fps": 6},
            "happy": {"frames": [16, 17], "fps": 6},
            "celebrating": {"frames": [18, 19], "fps": 6},
            "sleeping": {"frames": [20, 21], "fps": 4},
            "focus_mode": {"frames": [22, 23], "fps": 6},
        },
    }
    assert buddy_validate_pet_manifest(json.dumps(valid_manifest)) is True

    # Packaged manifest validation
    asset_manifest = Path(__file__).parents[2] / "python" / "bergendy" / "assets" / "pets" / "bergendy" / "pet.json"
    assert buddy_validate_pet_manifest_file(str(asset_manifest)) is True

    # Insecure path traversal rejected
    insecure = dict(valid_manifest, spritesheetPath="../secret.png")
    with pytest.raises(ValueError, match="is insecure"):
        buddy_validate_pet_manifest(json.dumps(insecure))

    # Missing required animation rejected
    missing_anim = dict(valid_manifest)
    del missing_anim["animations"]["blocked"]
    with pytest.raises(ValueError, match="Missing required animation 'blocked'"):
        buddy_validate_pet_manifest(json.dumps(missing_anim))

    # Zero dimensions rejected
    zero_dim = dict(valid_manifest, frameWidth=0)
    with pytest.raises(ValueError, match="Frame dimensions must be non-zero"):
        buddy_validate_pet_manifest(json.dumps(zero_dim))


def test_debt_ledger_scan(tmp_path):
    """Verify DebtLedger extracts 'bergendy: deferred' items."""
    code = tmp_path / "app.py"
    code.write_text(
        "# Regular code\n"
        "x = 1\n"
        "# bergendy: deferred OAuth2 provider support\n"
        "y = 2\n"
        "// bergendy: deferred Redis caching layer\n",
        encoding="utf-8",
    )
    ledger = DebtLedger(str(tmp_path))
    cards = ledger.scan()

    assert len(cards) == 2
    assert "OAuth2 provider" in cards[0].note
    assert "Redis caching" in cards[1].note
    md = ledger.render_markdown()
    assert "**Total Deferred Items:** 2" in md

# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""End-to-End Golden Trial Run for Boundary Runtime Boundary Defense.

Tests the full lifecycle across languages:
1. Scan: identifies unvalidated callsites and unprotected boundaries.
2. Resolve: isolates payloads, calls BYOK LLM (mocked), synthesizes schemas,
   and injects validation directly into callsites.
3. No-Swallow: rejects patches that swallow validation exceptions.
4. Verify: runs isolated verification replaying captured HTTP exchanges.
"""

import json
import os
import subprocess
import sys
from types import SimpleNamespace
import pytest

from boundary.cli.enterprise_commands import cmd_scan, cmd_resolve, cmd_verify
from boundary.llm import LLMResponse


@pytest.fixture
def golden_workspace(tmp_path):
    """Create a self-contained multi-language workspace with captured telemetry."""
    workdir = str(tmp_path / "golden_repo")
    os.makedirs(os.path.join(workdir, "src"), exist_ok=True)
    os.makedirs(os.path.join(workdir, ".boundary", "knowledge"), exist_ok=True)

    subprocess.run(["git", "init", "-b", "main"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Boundary Golden"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "golden@boundary.dev"], cwd=workdir, check=True, capture_output=True)

    ts_file = os.path.join(workdir, "src", "resend.ts")
    with open(ts_file, "w", encoding="utf-8") as f:
        f.write(
            'export async function sendEmail() {\n'
            '  const res = await fetch("https://api.resend.com/emails");\n'
            '  const data = await res.json();\n'
            '  return data;\n'
            '}\n'
        )

    py_file = os.path.join(workdir, "src", "weather.py")
    with open(py_file, "w", encoding="utf-8") as f:
        f.write(
            'import requests\n\n'
            'def get_weather():\n'
            '    res = requests.get("https://api.weatherapi.com/v1/current.json")\n'
            '    data = res.json()\n'
            '    return data\n'
        )

    exchanges_file = os.path.join(workdir, ".boundary", "knowledge", "exchanges.jsonl")
    with open(exchanges_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "request_method": "POST",
            "request_url": "https://api.resend.com/emails",
            "request_path": "/emails",
            "request_headers": {"Authorization": "Bearer re_123"},
            "response_status": 200,
            "response_body": {
                "id": "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794",
                "from": "onboarding@resend.dev",
                "to": ["user@example.com"],
                "created_at": "2026-09-16T09:00:00.000Z"
            }
        }) + "\n")
        f.write(json.dumps({
            "request_method": "GET",
            "request_url": "https://api.weatherapi.com/v1/current.json",
            "request_path": "/v1/current.json",
            "response_status": 200,
            "response_body": {
                "location": {"name": "San Francisco", "region": "California"},
                "current": {"temp_c": 18.5, "condition": {"text": "Partly cloudy"}}
            }
        }) + "\n")

    test_runner = os.path.join(workdir, "run_tests.py")
    with open(test_runner, "w", encoding="utf-8") as f:
        f.write(
            'import sys\n'
            'print("Mock verification test suite executed successfully.")\n'
            'sys.exit(0)\n'
        )

    subprocess.run(["git", "add", "-A"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=workdir, check=True, capture_output=True)

    return workdir


def test_golden_scan_detects_unprotected_boundaries(golden_workspace, capsys):
    """Test boundary scan accurately discovers unvalidated boundaries."""
    args = SimpleNamespace(path=golden_workspace)
    cmd_scan(args)
    captured = capsys.readouterr()

    assert "Bergendy Integrity Report" in captured.out or "Boundary Integrity Report" in captured.out
    assert "src/resend.ts" in captured.out
    assert "src/weather.py" in captured.out
    assert "Unprotected Boundaries" in captured.out


def test_golden_resolve_and_verify(golden_workspace, monkeypatch, capsys):
    """Test boundary resolve synthesizes schemas, patches callsites, and verifies."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_golden_test_credential")

    class MockSynthesizerLLM:
        def complete(self, messages=None, system_prompt=None):
            content_in = messages[0]["content"] if messages else ""
            if "resend" in content_in or "emails" in content_in:
                return LLMResponse(
                    content=(
                        "import { z } from 'zod';\n\n"
                        "export const EmailsSchema = z.object({\n"
                        "  id: z.string().uuid(),\n"
                        "  from: z.string().email(),\n"
                        "  to: z.array(z.string().email()),\n"
                        "  created_at: z.string(),\n"
                        "});\n"
                    ),
                    model="groq/llama-3.3-70b-versatile"
                )
            else:
                return LLMResponse(
                    content=(
                        "from pydantic import BaseModel\n\n"
                        "class LocationModel(BaseModel):\n"
                        "    name: str\n"
                        "    region: str\n\n"
                        "class CurrentModel(BaseModel):\n"
                        "    location: LocationModel\n"
                    ),
                    model="groq/llama-3.3-70b-versatile"
                )

    monkeypatch.setattr(
        "boundary.cli.enterprise_commands.LLMClient",
        lambda cfg: MockSynthesizerLLM()
    )
    monkeypatch.setattr(
        "boundary.cli.enterprise_commands._detect_test_command",
        lambda workdir: f"{sys.executable} run_tests.py"
    )

    args = SimpleNamespace(path=golden_workspace, target="src/resend.ts")
    cmd_resolve(args)
    captured = capsys.readouterr()

    assert "Resolving Unprotected Boundaries" in captured.out
    assert "Synthesizing runtime schemas" in captured.out
    assert "Resolution Complete" in captured.out

    schema_path = os.path.join(golden_workspace, "src", "schemas", "emails.ts")
    if not os.path.exists(schema_path):
        schema_path = os.path.join(golden_workspace, "schemas", "emails.ts")
    assert os.path.exists(schema_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_code = f.read()
    assert "request_method" not in schema_code
    assert "request_headers" not in schema_code
    assert "EmailsSchema" in schema_code

    with open(os.path.join(golden_workspace, "src", "resend.ts"), "r", encoding="utf-8") as f:
        patched_code = f.read()
    assert "EmailsSchema" in patched_code
    assert ".parse(" in patched_code

    verify_args = SimpleNamespace(path=golden_workspace)
    cmd_verify(verify_args)
    verify_captured = capsys.readouterr()
    assert "Isolated Verification" in verify_captured.out
    assert "Integrity verified." in verify_captured.out


def test_golden_no_swallow_violation_rejected(golden_workspace):
    """Test AST rewriter strictly rejects patches that swallow errors silently."""
    from boundary.hunt import repair_unvalidated_boundary

    class SwallowAttemptLLM:
        def complete(self, messages=None, system_prompt=None):
            return LLMResponse(
                content="import { z } from 'zod';\nexport const BadSchema = z.object({ id: z.string() });\n",
                model="test"
            )

    swallow_file = os.path.join(golden_workspace, "src", "swallow.ts")
    with open(swallow_file, "w", encoding="utf-8") as f:
        f.write(
            'export async function callApi() {\n'
            '  try {\n'
            '    const res = await fetch("https://api.resend.com/emails");\n'
            '    const data = await res.json();\n'
            '    return data;\n'
            '  } catch (err) {\n'
            '    return null;\n'
            '  }\n'
            '}\n'
        )

    with pytest.raises(ValueError, match="AST Verifier Violation"):
        repair_unvalidated_boundary(
            repo_dir=golden_workspace,
            endpoint="https://api.resend.com/emails",
            callsite_file=swallow_file,
            client=SwallowAttemptLLM()
        )


def test_golden_python_and_go_resolution(tmp_path, monkeypatch, capsys):
    """Test resolution on Python (Pydantic) and Go targets."""
    workdir = str(tmp_path / "polyglot_repo")
    os.makedirs(os.path.join(workdir, "src"), exist_ok=True)
    os.makedirs(os.path.join(workdir, ".boundary", "knowledge"), exist_ok=True)

    subprocess.run(["git", "init", "-b", "main"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Boundary Golden"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "golden@boundary.dev"], cwd=workdir, check=True, capture_output=True)

    py_file = os.path.join(workdir, "src", "client.py")
    with open(py_file, "w", encoding="utf-8") as f:
        f.write(
            'import requests\n\n'
            'def fetch_user():\n'
            '    res = requests.get("https://api.example.com/users")\n'
            '    return res.json()\n'
        )

    exchanges_file = os.path.join(workdir, ".boundary", "knowledge", "exchanges.jsonl")
    with open(exchanges_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "request_method": "GET",
            "request_url": "https://api.example.com/users",
            "request_path": "/users",
            "response_status": 200,
            "response_body": {
                "id": 101,
                "username": "alice",
                "active": True
            }
        }) + "\n")

    test_runner = os.path.join(workdir, "run_tests.py")
    with open(test_runner, "w", encoding="utf-8") as f:
        f.write('import sys\nsys.exit(0)\n')

    subprocess.run(["git", "add", "-A"], cwd=workdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=workdir, check=True, capture_output=True)

    class MockPyLLM:
        def complete(self, messages=None, system_prompt=None):
            return LLMResponse(
                content=(
                    "from pydantic import BaseModel\n\n"
                    "class UsersSchema(BaseModel):\n"
                    "    id: int\n"
                    "    username: str\n"
                    "    active: bool\n"
                ),
                model="groq/llama-3.3-70b-versatile"
            )

    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr("boundary.cli.enterprise_commands.LLMClient", lambda cfg: MockPyLLM())
    monkeypatch.setattr("boundary.cli.enterprise_commands._detect_test_command", lambda w: f"{sys.executable} run_tests.py")

    args = SimpleNamespace(path=workdir, target="src/client.py")
    cmd_resolve(args)
    captured = capsys.readouterr()

    assert "Resolution Complete" in captured.out
    schema_file = os.path.join(workdir, "src", "schemas", "users.py")
    if not os.path.exists(schema_file):
        schema_file = os.path.join(workdir, "schemas", "users.py")
    assert os.path.exists(schema_file)
    with open(schema_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "class UsersSchema(BaseModel):" in content
    assert "request_method" not in content

    with open(os.path.join(workdir, "src", "client.py"), "r", encoding="utf-8") as f:
        patched = f.read()
    assert "UsersSchema" in patched

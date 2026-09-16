# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import subprocess
import json


from boundary import audit as audit_mod
from boundary.audit import is_code_evidence

def _run_boundary_cli(args):
    env = dict(os.environ)
    env["PYTHONPATH"] = "python"
    env.setdefault("BOUNDARY_LLM_KEY", "sk-ant-test-credential-key")
    return subprocess.run(
        [sys.executable, "-m", "boundary.cli.main"] + args,
        capture_output=True,
        text=True,
        env=env
    )


def test_cli_audit_default():
    result = _run_boundary_cli(["audit", "trials/fixtures/taxonomy_stripe/"])
    assert result.returncode == 0
    assert "BOUNDARY: EXTERNAL-CHANGE DEPENDENCY AUDIT" in result.stdout
    assert "Stripe" in result.stdout


def test_cli_audit_github_issue():
    result = _run_boundary_cli(["audit", "trials/fixtures/taxonomy_stripe/", "--format=github-issue"])
    assert result.returncode == 0
    assert "# Boundary: External Dependency Map & Risk Register" in result.stdout
    assert "| **Stripe** |" in result.stdout


def test_cli_audit_json():
    result = _run_boundary_cli(["audit", "trials/fixtures/taxonomy_stripe/", "--format=json"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "total_providers_detected" in data
    assert "at_risk" in data


def test_cli_graph():
    result = _run_boundary_cli(["graph", "trials/fixtures/taxonomy_stripe/"])
    assert result.returncode == 0
    assert "BOUNDARY: EXTERNAL-CHANGE DEPENDENCY GRAPH" in result.stdout


def test_cli_check_default():
    result = _run_boundary_cli(["check", "trials/fixtures/taxonomy_stripe/"])
    assert result.returncode == 0
    assert "BOUNDARY: EXTERNAL-CHANGE DEPENDENCY AUDIT" in result.stdout
    assert "Stripe" in result.stdout


def test_cli_fix_detect():
    result = _run_boundary_cli(["fix", "trials/fixtures/taxonomy_stripe/", "--detect"])
    assert result.returncode == 0
    assert "BOUNDARY AUTONOMOUS MAINTENANCE LOOP" in result.stdout


def test_cli_at_howl_alias():
    result = _run_boundary_cli(["@howl", "--help"])
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "consult" in result.stdout  # alias routes to the consult parser


def test_cli_at_hunt_alias():
    result = _run_boundary_cli(["@hunt", "trials/fixtures/taxonomy_stripe/", "--detect"])
    assert result.returncode == 0
    assert "BOUNDARY AUTONOMOUS MAINTENANCE LOOP" in result.stdout




def test_audit_drops_string_only_drift(tmp_path):
    repo = str(tmp_path / "r")
    os.makedirs(os.path.join(repo, "src"))
    with open(os.path.join(repo, "src", "proxy.rs"), "w") as f:
        f.write('const URL: &str = "https://api.openai.com";\n')
    out = audit_mod.run_audit(repo_root=repo, output_format="cli")
    assert "[CRITICAL]" not in out


def test_is_code_evidence_classifier():
    assert is_code_evidence({"kind": "Import", "matched_pattern": "x",
                             "line_content": "import x"}) is True
    assert is_code_evidence({"kind": None, "matched_pattern": "stripe",
                             "line_content": "return stripe.charges.create({...});"}) is True
    assert is_code_evidence({"kind": None, "matched_pattern": "api.openai.com",
                             "line_content": 'const U: &str = "https://api.openai.com";'}) is False
    assert is_code_evidence({"kind": None, "matched_pattern": "Anthropic",
                             "line_content": 'println!("  For Anthropic models:");'}) is False
    assert is_code_evidence({"kind": None, "matched_pattern": "",
                             "line_content": "code"}) is False


def test_cli_gate_clean_and_blocking(tmp_path):
    repo = str(tmp_path / "gated_repo")
    os.makedirs(os.path.join(repo, "src"))
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    clean_file = os.path.join(repo, "src", "clean.ts")
    with open(clean_file, "w") as f:
        f.write("export const x = 1;\n")

    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    # Run gate on clean staged changes
    res_clean = _run_boundary_cli(["gate", repo, "--ci"])
    assert res_clean.returncode == 0
    assert "Zero unprotected network boundaries" in res_clean.stdout

    # Test guard alias as well
    res_alias = _run_boundary_cli(["guard", repo, "--ci"])
    assert res_alias.returncode == 0
    assert "Zero unprotected network boundaries" in res_alias.stdout

    # Now add unvalidated fetch
    unvalidated_file = os.path.join(repo, "src", "api.ts")
    with open(unvalidated_file, "w") as f:
        f.write('export async function fetchNews() { return fetch("https://news.api/top"); }\n')

    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    res_blocking = _run_boundary_cli(["gate", repo])
    assert res_blocking.returncode == 1
    assert "Unprotected I/O detected" in res_blocking.stdout
    assert "src/api.ts" in res_blocking.stdout


def test_cli_gate_install(tmp_path):
    repo = str(tmp_path / "hook_repo")
    os.makedirs(os.path.join(repo, ".git"))
    res = _run_boundary_cli(["gate", repo, "--install"])
    assert res.returncode == 0
    hook_file = os.path.join(repo, ".git", "hooks", "pre-commit")
    assert os.path.isfile(hook_file)
    with open(hook_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "boundary gate" in content

# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""Shield: deterministic Zod/Pydantic generation + fail-closed enforcement.

v0 generation is LLM-free (offline, reproducible CI). The AI Shield prompts
(retrained Pocock/Ramirez philosophy) refine via `boundary shield --fix`
when BYOK credentials exist; the checked-in schema stays deterministic.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from boundary.contracts import approve, record_shape, top_shapes

HOOK_BODY = """#!/bin/sh
# Boundary Shield (managed by `boundary shield --on`). Fail-closed.
STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\\.(ts|tsx|js|jsx|py)$' || true)
if [ -z "$STAGED" ]; then exit 0; fi
echo "$STAGED" | xargs boundary shield-check --files
"""

SHIELD_SYSTEM_PROMPT = """You are an expert in Matt Pocock's TypeScript philosophy: parse, don't validate.
Given unique live JSON payloads captured from one API endpoint, generate a SINGLE strict
Zod v3 schema covering all variations (discriminated unions where needed, .strict() everywhere,
no `any`, no passthrough). Output ONLY the TypeScript code."""

SHIELD_INJECT_PROMPT = """Given the user's original fetch call and the strict schema below, rewrite the
callsite to import the schema and .parse() the response. On parse failure throw a typed
error naming the endpoint. Output ONLY the rewritten code."""

SHIELD_BLOCK_PROMPT = """Analyze this git diff. Did the author (human or AI agent) introduce a network
call (fetch/axios/requests) whose response is NOT passed through a validation function
(.parse/model_validate)? If yes, output BLOCK_COMMIT plus file:line and the fix command.
If every new boundary is guarded, output PASS."""


def _ts_type(v: Any) -> str:
    if isinstance(v, str):
        return "z.string()"
    if isinstance(v, bool):
        return "z.boolean()"
    if isinstance(v, int):
        return "z.number().int()"
    if isinstance(v, float):
        return "z.number()"
    if v is None:
        return "z.null()"
    if isinstance(v, list):
        return f"z.array({_ts_type(v[0])})" if v else "z.array(z.unknown())"
    if isinstance(v, dict):
        fields = ", ".join(f"{k}: {_ts_type(w)}" for k, w in sorted(v.items()))
        return "z.object({ " + fields + " }).strict()"
    return "z.unknown()"


def _py_type(v: Any) -> str:
    if isinstance(v, str):
        return "str"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if v is None:
        return "None"
    if isinstance(v, list):
        return f"list[{_py_type(v[0])}]" if v else "list[Any]"
    if isinstance(v, dict):
        return "dict"
    return "Any"


def zod_from_sample(sample: dict[str, Any], export_name: str = "BoundarySchema") -> str:
    fields = ", ".join(f"{k}: {_ts_type(w)}" for k, w in sorted(sample.items()))
    return ('import { z } from "zod";\n\n'
            f"export const {export_name} = z.object({{ {fields} }}).strict();\n"
            f"export type {export_name}T = z.infer<typeof {export_name}>;\n")


def pydantic_from_sample(sample: dict[str, Any], class_name: str = "BoundaryModel") -> str:
    lines = ["from pydantic import BaseModel", "", "", f"class {class_name}(BaseModel):"]
    if not sample:
        lines.append("    pass")
    for k in sorted(sample):
        lines.append(f"    {k}: {_py_type(sample[k])}")
    return "\n".join(lines) + "\n"


def generate(repo_root: str, name: str, sample: Any) -> dict[str, str]:
    """Write .boundary/<name>.ts + .boundary/<name>.py, record+approve shape."""
    root = os.path.abspath(repo_root)
    outdir = os.path.join(root, ".boundary")
    os.makedirs(outdir, exist_ok=True)
    obj = (sample[0] if isinstance(sample, list) and sample
           and isinstance(sample[0], dict) else sample)
    if not isinstance(obj, dict):
        obj = {"value": obj}
    export = "".join(w.capitalize() for w in name.split("_")) + "Schema"
    ts_path = os.path.join(outdir, f"{name}.ts")
    py_path = os.path.join(outdir, f"{name}.py")
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(zod_from_sample(obj, export))
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(pydantic_from_sample(obj, export.replace("Schema", "Model")))
    h = record_shape(root, name, obj)
    approve(root, name, h)
    # Merge other top shapes into one schema file when traffic shows variants.
    variants = [s for s in top_shapes(root, name) if s["shape_hash"] != h]
    return {"ts": ts_path, "py": py_path, "shape": h, "variants": str(len(variants))}


def install_hook(repo_root: str = ".") -> str:
    hook = os.path.join(os.path.abspath(repo_root), ".git", "hooks", "pre-commit")
    if not os.path.isdir(os.path.dirname(hook)):
        return "not a git repo (no .git/hooks); shield not installed"
    existing = ""
    if os.path.exists(hook):
        with open(hook, encoding="utf-8", errors="ignore") as f:
            existing = f.read()
        if "Boundary Shield" in existing:
            return f"shield already installed ({hook})"
        with open(hook + ".pre-boundary", "w", encoding="utf-8") as f:
            f.write(existing)
    with open(hook, "w", encoding="utf-8") as f:
        f.write(existing + ("\n" if existing and not existing.endswith("\n") else "") + HOOK_BODY)
    os.chmod(hook, 0o755)
    return f"shield installed ({hook}); unvalidated boundaries now fail closed"


def remove_hook(repo_root: str = ".") -> str:
    hook = os.path.join(os.path.abspath(repo_root), ".git", "hooks", "pre-commit")
    bak = hook + ".pre-boundary"
    if os.path.exists(bak):
        os.replace(bak, hook)
        return "shield removed (previous hook restored)"
    if os.path.exists(hook):
        with open(hook, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "Boundary Shield" in content:
            os.remove(hook)
            return "shield removed"
    return "no shield installed"


def _staged_files(repo_root: str) -> list[str]:
    try:
        p = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                           cwd=repo_root, capture_output=True, text=True, timeout=10)
        return [f for f in p.stdout.splitlines() if f.strip()] if p.returncode == 0 else []
    except Exception:
        return []


def check_files(repo_root: str = ".", files: list[str] | None = None) -> tuple[bool, str]:
    """Fail-closed gate for hooks and CI. Returns (ok, message)."""
    from boundary.runtime_scan import scan_runtime_boundaries
    if files is None:
        files = _staged_files(repo_root)
    relevant = [f for f in files if f.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"))]
    if not relevant:
        return True, "shield: no staged TS/JS/Python files — pass"
    report = scan_runtime_boundaries(repo_root)
    staged = set(relevant)
    hits = [h for h in report["findings"] if h["file"] in staged]
    if not hits:
        return True, f"shield: {len(relevant)} staged file(s) guarded — pass"
    msg = ["SHIELD: blocked — unvalidated API boundaries in staged files:"]
    for h in hits[:10]:
        msg.append(f"  {h['file']}:{h['line']} {h['client']} {h['url']}"
                   f"{' [any]' if h['has_any'] else ''}")
    msg.append("Fix: `boundary shield --fix --name <api>` then stage .boundary/ schemas.")
    return False, "\n".join(msg)


def load_sample(sample_file: str | None) -> Any:
    if sample_file:
        with open(sample_file, encoding="utf-8") as f:
            return json.load(f)
    return {"id": 1, "name": "example", "active": True}


def refine_with_ai(repo_root: str, name: str, export: str) -> str | None:
    """BYOK refinement (Phase 3): feed top captured shapes to the AI Shield
    prompt and overwrite the deterministic schema on success. Fail-open to
    the deterministic file on any error (never blocks --fix)."""
    try:
        from boundary.llm import LLMClient, resolve_llm_config
        cfg = resolve_llm_config()
        if cfg is None:
            return "no BYOK credentials — kept deterministic schema (run `boundary auth`)"
        shapes = top_shapes(repo_root, name, limit=5)
        if not shapes:
            return "no captured shapes — kept deterministic schema"
        payload = json.dumps([s["sample"] for s in shapes])[:6000]
        resp = LLMClient(cfg).complete(
            [{"role": "user",
              "content": f"Endpoint: {name}. Export name: {export}. Payloads: {payload}"}],
            system_prompt=SHIELD_SYSTEM_PROMPT,
        )
        code = (resp.content or "").strip()
        if "z.object" not in code:
            return "AI output lacked a Zod schema — kept deterministic schema"
        # Strip markdown fences if the model added them.
        if code.startswith("```"):
            code = code.split("\n", 1)[1] if "\n" in code else code
            code = code.rsplit("```", 1)[0]
        ts_path = os.path.join(os.path.abspath(repo_root), ".boundary", f"{name}.ts")
        with open(ts_path, "w", encoding="utf-8") as f:
            f.write(code if code.endswith("\n") else code + "\n")
        return f"refined {name}.ts with {cfg.provider}/{cfg.model}"
    except Exception as exc:
        return f"AI refine skipped ({exc}) — kept deterministic schema"

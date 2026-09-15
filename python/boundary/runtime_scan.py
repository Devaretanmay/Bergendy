# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""Runtime boundary scanner: unvalidated external calls (Scout input).

TypeScript/JS: fetch(), axios.*, ky, ofetch without an adjacent .parse().
Python: requests.*, httpx.*, urlopen without model_validate/pydantic guard.
Fast regex line-scan layered under the Rust AST graph (authoritative for
SDK drift); this module is authoritative for *runtime validation* gaps.
"""

from __future__ import annotations

import os
import re
from typing import Any

TS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
PY_EXTS = (".py",)
GO_EXTS = (".go",)

TS_CALL = re.compile(
    r"(?<!\w)(fetch\s*\(|axios\s*\.\s*(get|post|put|patch|delete)\s*\(|"
    r"ky\s*\.\s*(get|post)\s*\(|ofetch\s*\()"
)
PY_CALL = re.compile(
    r"(?<!\w)(requests\s*\.\s*(get|post|put|patch|delete)\s*\(|"
    r"httpx\s*\.\s*(get|post|request)\s*\(|urlopen\s*\()"
)
GO_CALL = re.compile(
    r"(?<!\w)(http\s*\.\s*(Get|Post|Head|PostForm)\s*\(|"
    r"\w+\s*\.\s*(Get|Post|Do)\s*\(|"
    r"http\s*\.\s*NewRequest\s*\()"
)
URL_LIT = re.compile(r"""['"`](https?://[^'"`\s]+|/api/[^'"`\s]*)['"`]""")
PARSE_GUARD = re.compile(r"\.parse\s*\(|Schema\.parse|model_validate|pydantic|z\.object|zod|json\.Unmarshal")
ANY_CAST = re.compile(r"\bas\s+any\b|:\s*any\b|\bany\[\]|interface\{\}|any")

SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "target",
             ".boundary", "dist", "build"}


def _iter_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(TS_EXTS) or fn.endswith(PY_EXTS) or fn.endswith(GO_EXTS):
                yield os.path.join(dirpath, fn)


def scan_runtime_boundaries(repo_root: str = ".") -> dict[str, Any]:
    repo_root = os.path.abspath(repo_root)
    findings: list[dict[str, Any]] = []
    files_scanned = 0
    for fp in _iter_files(repo_root):
        try:
            with open(fp, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        files_scanned += 1
        if fp.endswith(PY_EXTS):
            lang = "python"
        elif fp.endswith(GO_EXTS):
            lang = "go"
        else:
            lang = "typescript"
        rel = os.path.relpath(fp, repo_root)
        for i, line in enumerate(lines):
            if lang == "typescript":
                call = TS_CALL.search(line)
            elif lang == "python":
                call = PY_CALL.search(line)
            else:
                call = GO_CALL.search(line)
            if not call:
                continue
            window = "".join(lines[max(0, i - 1):min(len(lines), i + 4)])
            url_m = URL_LIT.search(window) or URL_LIT.search(line)
            url = url_m.group(1) if url_m else "unknown-url"
            guarded = bool(PARSE_GUARD.search(window))
            has_any = bool(ANY_CAST.search(window))
            if guarded and not has_any:
                continue
            findings.append({
                "id": f"runtime-{abs(hash(rel + str(i))) % 0xFFFFFF:06x}",
                "file": rel,
                "line": i + 1,
                "lang": lang,
                "client": call.group(0).strip()[:32],
                "url": url,
                "guarded": guarded,
                "has_any": has_any,
                "line_content": line.strip()[:200],
            })
    return {
        "files_scanned": files_scanned,
        "total_boundaries": len(findings),
        "unvalidated": len(findings),
        "findings": findings,
    }


def boundary_score(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings", [])
    any_count = sum(1 for f in findings if f.get("has_any"))
    score = max(0, 100 - report.get("unvalidated", 0) * 15 - any_count * 5)
    grade = ("A — shielded" if score >= 90 else
             "B — mostly guarded" if score >= 70 else
             "C — exposed" if score >= 40 else "D — vibe-coded")
    return {"score": score, "grade": grade, "unvalidated": report.get("unvalidated", 0),
            "any_casts": any_count, "files_scanned": report.get("files_scanned", 0)}


def render_score(score: dict[str, Any]) -> str:
    return (
        "=" * 64 + "\n"
        f"  BOUNDARY SCORE: {score['score']}/100 — {score['grade']}\n"
        + "=" * 64 + "\n"
        f"  files scanned:      {score['files_scanned']}\n"
        f"  unvalidated calls:  {score['unvalidated']}\n"
        f"  `any` casts:        {score['any_casts']}\n"
        + "=" * 64
    )

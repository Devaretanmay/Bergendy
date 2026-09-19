# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""Boundary runtime layer: scanner, score, schemas, contracts, capture."""

from __future__ import annotations

import json
import os
import socket
import threading

from boundary import shield as sh
from boundary.capture import handle_frame
from boundary.contracts import (
    approve,
    check_drift,
    record_shape,
    shape_hash,
    status,
    top_shapes,
)
import tempfile
from boundary.runtime_scan import boundary_score, scan_runtime_boundaries


def _write(root: str, rel: str, content: str) -> None:
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


def test_guarded_callsite_passes(tmp_path):
    _write(str(tmp_path), "src/ok.ts",
           'import { z } from "zod";\nconst S = z.object({id: z.string()}).strict();\n'
           'export async function ok(){ const r = await fetch("https://api.x.com/v1/ok");'
           ' return S.parse(await r.json()); }\n')
    assert scan_runtime_boundaries(str(tmp_path))["unvalidated"] == 0


def test_unvalidated_fetch_and_any_flagged(tmp_path):
    _write(str(tmp_path), "src/bad.ts",
           'export async function bad(){ const r = await fetch("https://api.stripe.com/v1/c");'
           ' const d = await r.json() as any; return d; }\n')
    rep = scan_runtime_boundaries(str(tmp_path))
    assert rep["unvalidated"] == 1
    assert rep["findings"][0]["has_any"] is True
    assert boundary_score(rep)["score"] == 80


def test_python_requests_flagged(tmp_path):
    _write(str(tmp_path), "svc.py",
           'import requests\ndef g():\n    r = requests.get("https://api.stripe.com/v1/x")\n    return r.json()\n')
    assert scan_runtime_boundaries(str(tmp_path))["unvalidated"] == 1


def test_zod_strict_and_shape_dedup():
    assert shape_hash({"id": 1, "name": "a"}) == shape_hash({"id": 2, "name": "b"})
    z = sh.zod_from_sample({"id": 1}, "S")
    assert ".strict()" in z and "z.object" in z
    p = sh.pydantic_from_sample({"id": 1}, "M")
    assert "BaseModel" in p


def test_generate_writes_and_approves(tmp_path):
    out = sh.generate(str(tmp_path), "stripe", {"id": 1, "tax_id": "x"})
    assert os.path.isfile(out["ts"]) and os.path.isfile(out["py"])
    assert status(str(tmp_path))["tracked"] == 1


def test_contract_drift_detects_new_field(tmp_path):
    h = record_shape(str(tmp_path), "stripe", {"id": 1})
    approve(str(tmp_path), "stripe", h)
    assert check_drift(str(tmp_path), "stripe", {"id": 1}) is None
    d = check_drift(str(tmp_path), "stripe", {"id": 1, "tax_id": "x"})
    assert d and d["status"] == "drift" and d["live_keys"] == ["id", "tax_id"]
    assert len(status(str(tmp_path))["drifts"]) == 1


def test_capture_frame_roundtrip(tmp_path):
    # End-to-end socket path: frame in -> shape recorded in contracts.db.
    sock_path = os.path.join(tempfile.gettempdir(), f"boundary-test-{os.getpid()}.sock")
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(1)
    srv.settimeout(5)
    received = []

    def _serve():
        conn, _ = srv.accept()
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
        received.append(data)
        conn.close()
        srv.close()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(sock_path)
    c.sendall(json.dumps({"endpoint": "api/x", "sample": {"id": 1}}).encode() + b"\n")
    c.close()
    t.join(timeout=5)
    handle_frame(str(tmp_path), json.loads(received[0].decode()))
    assert top_shapes(str(tmp_path), "api/x")[0]["count"] == 1
    try:
        os.unlink(sock_path)
    except OSError:
        pass


def test_shield_hook_install_remove(tmp_path):
    repo = str(tmp_path / "r")
    os.makedirs(os.path.join(repo, ".git", "hooks"))
    assert "installed" in sh.install_hook(repo)
    assert "already" in sh.install_hook(repo)
    assert "removed" in sh.remove_hook(repo)

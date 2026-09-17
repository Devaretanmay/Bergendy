# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""Traffic interceptor: live payloads -> Contract Registry (local only).

`boundary dev -- <cmd>` spawns the app with BOUNDARY_CAPTURE=1 and a socket
path. The tiny boundary-sdk (sdk/boundary/) monkey-patches fetch/requests
and writes newline-delimited {endpoint, sample} frames to the socket.
This listener hashes shapes and tracks drift in .boundary/contracts.db.

No proxy, no MITM, no certificates broken, nothing leaves the machine.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import threading
from typing import Any

from bergendy.contracts import check_drift, record_shape


from bergendy.contracts import status as _status

def handle_frame(repo_root: str, frame: dict[str, Any]) -> None:
    endpoint = str(frame.get("endpoint") or "unknown").strip() or "unknown"
    sample = frame.get("sample", {})
    record_shape(repo_root, endpoint, sample)
    try:
        check_drift(repo_root, endpoint, sample)
    except Exception:
        pass


def serve(repo_root: str, sock_path: str, stop: threading.Event) -> None:
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(8)
    srv.settimeout(0.5)
    buf = b""
    while not stop.is_set():
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            conn.settimeout(0.5)
            while True:
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        handle_frame(repo_root, json.loads(line.decode("utf-8", "ignore")))
                    except Exception:
                        continue
        finally:
            conn.close()
    srv.close()
    try:
        if os.path.exists(sock_path):
            os.unlink(sock_path)
    except OSError:
        pass


def cmd_dev(args) -> int:
    """Run `boundary dev -- <cmd>`: capture live traffic into the registry."""
    repo_root = os.path.abspath(getattr(args, "path", ".") or ".")
    cmd = getattr(args, "cmd", None) or []
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("usage: boundary dev -- <command> (e.g. boundary dev -- npm run dev)")
        return 2
    sock_path = os.path.join(tempfile.gettempdir(), f"boundary-{os.getpid()}.sock")
    stop = threading.Event()
    t = threading.Thread(target=serve, args=(repo_root, sock_path, stop), daemon=True)
    t.start()
    env = dict(os.environ, BOUNDARY_CAPTURE="1", BOUNDARY_SOCKET=sock_path)
    print(f"boundary dev: capturing to {sock_path} — run traffic through the app, Ctrl-C to stop")
    try:
        proc = subprocess.run(cmd, cwd=repo_root, env=env)
        rc = proc.returncode
    except KeyboardInterrupt:
        rc = 130
    finally:
        stop.set()
        t.join(timeout=5)
    s = _status(repo_root)
    print(f"capture done: {s['tracked']} tracked endpoint(s), {len(s['drifts'])} drift event(s)")
    return rc

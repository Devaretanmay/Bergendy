# Copyright 2026 Boundary Authors
# SPDX-License-Identifier: Apache-2.0
"""Contract Registry: live JSON payload shapes per endpoint (local SQLite).

This is the runtime half of Boundary. The SDK-drift half lives in
providers/registry.py (kept intact). Together: SDK package changes AND
JSON payload shape changes are both covered.

Storage: <repo>/.boundary/contracts.db (stdlib sqlite3, zero deps).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS shapes (
  endpoint TEXT NOT NULL,
  shape_hash TEXT NOT NULL,
  sample TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 1,
  first_seen INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  PRIMARY KEY (endpoint, shape_hash)
);
CREATE TABLE IF NOT EXISTS approved (
  endpoint TEXT PRIMARY KEY,
  shape_hash TEXT NOT NULL,
  approved_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS drift_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  endpoint TEXT NOT NULL,
  live_hash TEXT NOT NULL,
  approved_hash TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  at INTEGER NOT NULL
);
"""


def db_path(repo_root: str) -> str:
    return os.path.join(os.path.abspath(repo_root), ".boundary", "contracts.db")


def _connect(repo_root: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path(repo_root)), exist_ok=True)
    conn = sqlite3.connect(db_path(repo_root))
    conn.executescript(SCHEMA)
    return conn


def shape_hash(payload: Any) -> str:
    """Structural hash: keys+types sorted, values stripped (dedup engine)."""

    def norm(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: norm(v[k]) for k in sorted(v)}
        if isinstance(v, list):
            inner = sorted({json.dumps(norm(x), sort_keys=True) for x in v[:10]})
            return [f"list[{i}]" for i in inner] or ["list[unknown]"]
        return type(v).__name__

    canon = json.dumps(norm(payload), sort_keys=True)
    return hashlib.blake2b(canon.encode(), digest_size=8).hexdigest()


def record_shape(repo_root: str, endpoint: str, sample: Any) -> str:
    """Store (or bump count of) a structural shape. Returns its hash."""
    h = shape_hash(sample)
    now = int(time.time())
    conn = _connect(repo_root)
    try:
        conn.execute(
            "INSERT INTO shapes(endpoint, shape_hash, sample, count, first_seen, last_seen)"
            " VALUES(?,?,?,?,?,?)"
            " ON CONFLICT(endpoint, shape_hash) DO UPDATE SET"
            " count=count+1, last_seen=excluded.last_seen",
            (endpoint, h, json.dumps(sample)[:8000], 1, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return h


def top_shapes(repo_root: str, endpoint: str, limit: int = 5) -> list[dict[str, Any]]:
    conn = _connect(repo_root)
    try:
        rows = conn.execute(
            "SELECT shape_hash, sample, count FROM shapes WHERE endpoint=? ORDER BY count DESC LIMIT ?",
            (endpoint, limit),
        ).fetchall()
    finally:
        conn.close()
    return [{"shape_hash": r[0], "sample": json.loads(r[1]), "count": r[2]} for r in rows]


def approve(repo_root: str, endpoint: str, shape_hash_: str) -> None:
    conn = _connect(repo_root)
    try:
        conn.execute(
            "INSERT INTO approved(endpoint, shape_hash, approved_at) VALUES(?,?,?)"
            " ON CONFLICT(endpoint) DO UPDATE SET shape_hash=excluded.shape_hash,"
            " approved_at=excluded.approved_at",
            (endpoint, shape_hash_, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


def check_drift(repo_root: str, endpoint: str, live_sample: Any) -> dict[str, Any] | None:
    """Compare a live payload against the approved shape. Logs drift events."""
    live_hash = shape_hash(live_sample)
    conn = _connect(repo_root)
    try:
        row = conn.execute("SELECT shape_hash FROM approved WHERE endpoint=?", (endpoint,)).fetchone()
        if row is None:
            return {"status": "untracked", "live_hash": live_hash}
        approved_hash = row[0]
        if approved_hash == live_hash:
            return None
        live_keys = sorted(live_sample.keys()) if isinstance(live_sample, dict) else []
        conn.execute(
            "INSERT INTO drift_events(endpoint, live_hash, approved_hash, detail, at)"
            " VALUES(?,?,?,?,?)",
            (endpoint, live_hash, approved_hash, json.dumps({"live_keys": live_keys}), int(time.time())),
        )
        conn.commit()
        return {"status": "drift", "endpoint": endpoint, "live_hash": live_hash,
                "approved_hash": approved_hash, "live_keys": live_keys}
    finally:
        conn.close()


def status(repo_root: str) -> dict[str, Any]:
    conn = _connect(repo_root)
    try:
        endpoints = [r[0] for r in conn.execute("SELECT endpoint FROM approved").fetchall()]
        drifts = conn.execute(
            "SELECT endpoint, live_hash, approved_hash, detail, at FROM drift_events"
            " ORDER BY id DESC LIMIT 20"
        ).fetchall()
    finally:
        conn.close()
    return {
        "tracked": len(endpoints),
        "drifts": [
            {"endpoint": d[0], "live_hash": d[1], "approved_hash": d[2],
             "detail": json.loads(d[3] or "{}"), "at": d[4]} for d in drifts
        ],
    }

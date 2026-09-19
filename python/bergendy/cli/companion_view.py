# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Companion View for Bergendy Engineering Buddy.

Renders terminal-native ASCII expressions and provides a lightweight stdlib
HTTP/SSE overlay server for on-screen pet animation.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional

PET_FACES = {
    "idle": "( - . - )",
    "watching": "( • _ • )",
    "thinking": "( ˘ ʖ ̯ ˘ )",
    "curious": "( o _ O )",
    "suspicious": "( ¬ _ ¬ )",
    "questioning": "( ? _ ? )",
    "concerned": "( . _ . )",
    "blocked": "( > _ < )",
    "happy": "( ^ _ ^ )",
    "celebrating": "\\( ^ o ^ )/",
    "sleeping": "( - _ - ) zzz",
    "focus_mode": "( • ̀ - • ́ )",
}

LEVEL_BADGES = {
    "Level0Silent": "\033[90m[WATCH]\033[0m",
    "Level1Visual": "\033[32m[CHEER]\033[0m",
    "Level2Nudge": "\033[33m[NUDGE]\033[0m",
    "Level3Challenge": "\033[35m[CHALLENGE]\033[0m",
    "Level4Block": "\033[31;1m[BLOCK]\033[0m",
}


class TerminalPetRenderer:
    """Renders ANSI/ASCII Bergendy buddy state in the terminal."""

    @staticmethod
    def render_bubble(speech: str, max_width: int = 50) -> list[str]:
        words = speech.split()
        lines = []
        current = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > max_width:
                lines.append(" ".join(current))
                current = [w]
                cur_len = len(w)
            else:
                current.append(w)
                cur_len += len(w) + 1
        if current:
            lines.append(" ".join(current))

        width = max(len(line) for line in lines) if lines else 10
        top = "  ." + "-" * (width + 2) + "."
        middle = [f"  | {line.ljust(width)} |" for line in lines]
        bottom = "  '" + "-" * (width + 2) + "'"
        pointer1 = "         \\"
        pointer2 = "          \\"
        return [top] + middle + [bottom, pointer1, pointer2]

    @classmethod
    def render(
        cls,
        state: str,
        speech: str,
        level: str = "Level0Silent",
        task_id: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
    ) -> str:
        face = PET_FACES.get(state, "( • _ • )")
        badge = LEVEL_BADGES.get(level, "[BUDDY]")
        task_info = f"\033[90m[{task_id}]\033[0m " if task_id else ""

        output_lines = []
        if speech:
            output_lines.extend(cls.render_bubble(speech))

        pet_line = f"           \033[1;36m{face}\033[0m  \033[1mBergendy\033[0m {task_info}{badge}"
        output_lines.append(pet_line)

        if evidence and evidence.get("evidence"):
            output_lines.append(f"             \033[90m↳ {evidence['evidence']}\033[0m")

        return "\n".join(output_lines)


class OverlayServer:
    """Lightweight stdlib HTTP/SSE server streaming buddy state to desktop webviews."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.latest_state = {
            "pet_state": "watching",
            "speech_bubble": "Watching... Looks good so far.",
            "level": "Level0Silent",
        }
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def update(self, state_dict: dict[str, Any]) -> None:
        self.latest_state.update(state_dict)

    def start(self) -> None:
        handler_cls = self._make_handler()
        self.server = HTTPServer((self.host, self.port), handler_cls)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _make_handler(self):
        parent = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # silence log output

            def do_GET(self):
                if self.path == "/state":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(parent.latest_state).encode("utf-8"))
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(HTML_OVERLAY.encode("utf-8"))

        return _Handler


HTML_OVERLAY = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Bergendy Companion</title>
  <style>
    body {
      margin: 0;
      background: transparent;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
      user-select: none;
    }
    #container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }
    #bubble {
      background: rgba(25, 25, 30, 0.92);
      color: #f0f0f0;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 12px;
      padding: 10px 14px;
      font-size: 13px;
      line-height: 1.4;
      max-width: 260px;
      margin-bottom: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      animation: pop 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    #pet-avatar {
      font-size: 28px;
      padding: 6px;
    }
    @keyframes pop {
      0% { transform: scale(0.85); opacity: 0; }
      100% { transform: scale(1); opacity: 1; }
    }
  </style>
</head>
<body>
  <div id="container">
    <div id="bubble">Watching... Looks good so far.</div>
    <div id="pet-avatar">( • _ • )</div>
  </div>
  <script>
    const faces = {
      idle: '( - . - )',
      watching: '( • _ • )',
      thinking: '( ˘ ʖ ̯ ˘ )',
      curious: '( o _ O )',
      suspicious: '( ¬ _ ¬ )',
      questioning: '( ? _ ? )',
      concerned: '( . _ . )',
      blocked: '( > _ < )',
      happy: '( ^ _ ^ )',
      celebrating: '\\( ^ o ^ )/',
      sleeping: '( - _ - ) zzz',
      focus_mode: '( • ̀ - • ́ )'
    };
    async function poll() {
      try {
        const res = await fetch('/state');
        const data = await res.json();
        document.getElementById('bubble').textContent = data.speech_bubble || 'Watching...';
        document.getElementById('pet-avatar').textContent = faces[data.pet_state] || '( • _ • )';
      } catch (e) {}
      setTimeout(poll, 600);
    }
    poll();
  </script>
</body>
</html>
"""

"""
Vercel serverless function — GET /api/examples
================================================
Returns metadata + raw .retro source for every demo program in /examples,
read live from the filesystem so the frontend always sees current source.
"""

import json
import os
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(ROOT, "examples")

CATALOG = [
    {
        "id": "neontetris",
        "file": "neontetris.retro",
        "title": "Neon Tetris",
        "desc": "7 standard pieces · NEON theme · full controls",
        "tag": "TETRIS",
        "color": "#b400ff",
    },
    {
        "id": "classictetris",
        "file": "classictetris.retro",
        "title": "Classic Tetris",
        "desc": "4 pieces · MONO theme · clean & minimal",
        "tag": "TETRIS",
        "color": "#00ffdc",
    },
    {
        "id": "minimaltetris",
        "file": "minimal_tetris.retro",
        "title": "Minimal Tetris",
        "desc": "Smallest valid RetroLang program",
        "tag": "TETRIS",
        "color": "#9696ff",
    },
    {
        "id": "snake",
        "file": "snake.retro",
        "title": "CRT Snake",
        "desc": "Classic Snake · CRT-green phosphor theme",
        "tag": "SNAKE",
        "color": "#00ff78",
    },
    {
        "id": "fastsnake",
        "file": "fastsnake.retro",
        "title": "Fast Snake",
        "desc": "AMBER theme · wrap-around edges · WASD keys",
        "tag": "SNAKE",
        "color": "#ffb000",
    },
]


def _load():
    out = []
    for entry in CATALOG:
        path = os.path.join(EXAMPLES_DIR, entry["file"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except OSError:
            source = ""
        out.append({**entry, "source": source})
    return out


class handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _send(self, status: int, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, _load())

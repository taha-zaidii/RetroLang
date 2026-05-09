"""
Vercel serverless function — POST /api/compile
================================================
Body  : { "source": "<.retro source>" }
Reply : { ok: true, ir: {...}, trace: {tokens, ast_nodes, tac_before, tac_after,
                                       optimization_log} }

The compiler in /src is the unmodified course project. This handler only
orchestrates the six phases and packages their output as JSON. Nothing in
/src is imported or shimmed — it runs exactly as it does on the CLI.
"""

import json
import os
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.lexer import tokenize
from src.parser import parse
from src.semantic import analyze
from src.ir import lower
from src.optimizer import optimize
from src.errors import RetroError, LexError, ParseError, SemanticError
from src.ast_nodes import Program


def _count_ast_nodes(program: Program) -> int:
    n = 1  # program itself
    n += 1  # header
    if program.pieces:
        n += 1 + len(program.pieces.pieces)
    if program.snake_mode:
        n += 1
    if program.rules:
        n += 1 + len(program.rules.rules)
    if program.controls:
        n += 1 + len(program.controls.bindings)
    return n


def _quad_to_list(q):
    return [str(q[0]), q[1], q[2], q[3]]


def _compile(source: str):
    tokens = tokenize(source)
    ast = parse(tokens, source)
    analyze(ast, source)
    ir, tac_before = lower(ast)
    tac_before_list = [_quad_to_list(q) for q in tac_before]
    ir, tac_after = optimize(ir, tac_before)
    tac_after_list = [_quad_to_list(q) for q in tac_after]
    return {
        "ok": True,
        "ir": asdict(ir),
        "trace": {
            "tokens": len(tokens),
            "ast_nodes": _count_ast_nodes(ast),
            "tac_before": tac_before_list,
            "tac_after": tac_after_list,
            "optimization_log": list(ir.optimization_log),
        },
    }


def _error_payload(phase: str, exc: Exception):
    return {"ok": False, "phase": phase, "message": str(exc)}


class handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # silence default access log
        pass

    def _send(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError as e:
            self._send(400, _error_payload("Request", e))
            return
        source = data.get("source")
        if not isinstance(source, str):
            self._send(400, _error_payload("Request", ValueError(
                "missing 'source' field (string)")))
            return
        try:
            self._send(200, _compile(source))
        except LexError as e:
            self._send(200, _error_payload("Lexer", e))
        except ParseError as e:
            self._send(200, _error_payload("Parser", e))
        except SemanticError as e:
            self._send(200, _error_payload("Semantic", e))
        except RetroError as e:
            self._send(200, _error_payload("Compiler", e))
        except Exception as e:  # pragma: no cover
            self._send(500, _error_payload("Internal", e))

    def do_GET(self):
        self._send(405, {"ok": False, "message": "POST a JSON body { source }"})

#!/usr/bin/env python3
"""
RetroLang Arcade — local dev server.

This is a lightweight local emulator of the Vercel deployment surface so you
can preview the arcade frontend offline:

  • routes /api/<name>  →  invokes the BaseHTTPRequestHandler class exported
                            by api/<name>.py
  • everything else     →  serves files from ./public/   (default ./)

It is NOT used in production — the live deployment is handled by Vercel's
Python runtime per ./api/*.py and the static assets in ./public/.

Usage:
    python3 dev_server.py            # default port 7373
    python3 dev_server.py 8080
"""

from __future__ import annotations
import importlib.util
import io
import mimetypes
import os
import socketserver
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT       = os.path.dirname(os.path.abspath(__file__))
API_DIR    = os.path.join(ROOT, "api")
PUBLIC_DIR = os.path.join(ROOT, "public")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_api_module(name: str):
    path = os.path.join(API_DIR, f"{name}.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location(f"_api_{name}", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# In-process invocation: feed the request into the api module's `handler`
# class without taking a second TCP hop. This mirrors how Vercel's Python
# runtime instantiates the handler for each invocation.
class _InMemoryRequest(io.BytesIO):
    def makefile(self, *_a, **_kw):
        return self


def _invoke_api_handler(handler_cls, method, path, headers_dict, body_bytes):
    raw = (
        f"{method} {path} HTTP/1.1\r\n"
        + "".join(f"{k}: {v}\r\n" for k, v in headers_dict.items())
        + "\r\n"
    ).encode("utf-8") + (body_bytes or b"")
    rfile = io.BytesIO(raw)
    wfile = io.BytesIO()

    class _FakeSocket:
        def __init__(self, rf, wf):
            self.rfile = rf
            self.wfile = wf
        def makefile(self, mode, *_a, **_kw):
            return self.rfile if "r" in mode else self.wfile
        def sendall(self, data): self.wfile.write(data)
        def getsockname(self): return ("127.0.0.1", 0)
        def getpeername(self): return ("127.0.0.1", 0)
        def close(self): pass

    sock = _FakeSocket(rfile, wfile)
    handler_cls(sock, ("127.0.0.1", 0), None)
    return wfile.getvalue()


class DevHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(f"  [{self.command}] {self.path}\n")

    def _serve_static(self, rel_path: str):
        # default doc
        if rel_path in ("", "/"):
            rel_path = "index.html"
        # security: no traversal
        rel_path = rel_path.lstrip("/")
        full = os.path.normpath(os.path.join(PUBLIC_DIR, rel_path))
        if not full.startswith(PUBLIC_DIR):
            self.send_error(403, "Forbidden"); return
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            self.send_error(404, "Not Found"); return
        ctype, _ = mimetypes.guess_type(full)
        ctype = ctype or "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _route_api(self, name: str):
        mod = _load_api_module(name)
        if mod is None or not hasattr(mod, "handler"):
            self.send_error(404, f"No /api/{name}")
            return
        # collect headers and optional body
        body = b""
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                body = self.rfile.read(length)
        # forward to the api module's handler class
        raw = _invoke_api_handler(
            mod.handler, self.command, self.path,
            dict(self.headers), body,
        )
        # raw is a complete HTTP/1.x response — write to client untouched
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _route(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            name = path[len("/api/"):].strip("/")
            return self._route_api(name)
        if path.startswith("/static/"):
            return self._serve_static(path[len("/"):])
        return self._serve_static(path)

    def do_GET(self):    self._route()
    def do_POST(self):   self._route()
    def do_OPTIONS(self):self._route()


class _ThreadedServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7373
    server = _ThreadedServer(("127.0.0.1", port), DevHandler)
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  RetroLang Arcade  →  {url}")
    print("  Static : ./public")
    print("  API    : ./api/*.py  (BaseHTTPRequestHandler-style)")
    print("  Ctrl+C to stop.\n")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()

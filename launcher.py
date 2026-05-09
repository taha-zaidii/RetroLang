#!/usr/bin/env python3
"""
RetroLang Demo Launcher  –  browser-based menu
----------------------------------------------
Opens a retro-styled page in your browser.
Click a game card → compiles the .retro file through all 6 phases → launches the game window.

Usage:
    python3.11 launcher.py
"""

import os, sys, subprocess, threading, webbrowser, tempfile, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src.lexer     import tokenize
from src.parser    import parse
from src.semantic  import analyze
from src.ir        import lower
from src.optimizer import optimize
from src.codegen   import generate
from src.errors    import RetroError

PORT = 7373

GAMES = [
    {"id": "neontetris",    "file": "examples/neontetris.retro",    "title": "Neon Tetris",    "desc": "7-piece Tetris · NEON theme · full controls", "tag": "TETRIS", "color": "#b400ff"},
    {"id": "classictetris", "file": "examples/classictetris.retro", "title": "Classic Tetris", "desc": "4-piece Tetris · MONO theme · minimal",         "tag": "TETRIS", "color": "#00ffdc"},
    {"id": "minimaltetris", "file": "examples/minimal_tetris.retro","title": "Minimal Tetris", "desc": "Smallest valid RetroLang program",               "tag": "TETRIS", "color": "#9696ff"},
    {"id": "snake",         "file": "examples/snake.retro",         "title": "CRT Snake",      "desc": "Classic Snake · CRT-green theme",               "tag": "SNAKE",  "color": "#00ff78"},
    {"id": "fastsnake",     "file": "examples/fastsnake.retro",     "title": "Fast Snake",     "desc": "AMBER Snake · wrap-around edges",                "tag": "SNAKE",  "color": "#ffb000"},
]

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RetroLang – Viva Demo Launcher</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:#06060f;font-family:'Share Tech Mono',monospace;color:#eee;min-height:100vh;
     display:flex;flex-direction:column;align-items:center;padding:40px 20px 60px;
     background-image:repeating-linear-gradient(0deg,transparent,transparent 37px,rgba(80,0,130,.08) 37px,rgba(80,0,130,.08) 38px),
                      repeating-linear-gradient(90deg,transparent,transparent 37px,rgba(80,0,130,.08) 37px,rgba(80,0,130,.08) 38px);}
h1{font-size:3rem;letter-spacing:.18em;text-align:center;margin-bottom:6px;
   background:linear-gradient(90deg,#b400ff,#00ffdc,#b400ff);background-size:200%;
   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
   animation:shine 3s linear infinite;}
@keyframes shine{0%{background-position:0%}100%{background-position:200%}}
.sub{color:#5a5a80;font-size:.8rem;text-align:center;margin-bottom:8px;letter-spacing:.12em}
.divider{width:640px;max-width:100%;height:1px;background:linear-gradient(90deg,transparent,#5000a0,transparent);margin:18px auto}
.prompt{color:#00ffdc;font-size:.78rem;text-align:center;letter-spacing:.14em;margin-bottom:28px}
.cards{display:flex;flex-direction:column;gap:14px;width:680px;max-width:100%}
.card{display:flex;align-items:center;gap:16px;background:#0d0d26;border:1px solid #5000a0;
      border-radius:10px;padding:16px 20px;cursor:pointer;transition:all .18s;position:relative;overflow:hidden;}
.card::before{content:'';position:absolute;inset:0;background:var(--glow);opacity:0;transition:opacity .2s;pointer-events:none}
.card:hover{border-color:var(--c);background:#1a0835;transform:translateX(4px)}
.card:hover::before{opacity:.07}
.badge{width:36px;height:36px;border-radius:6px;display:flex;align-items:center;justify-content:center;
       font-size:1.1rem;font-weight:bold;background:#5000a0;color:#fff;flex-shrink:0;transition:background .18s}
.card:hover .badge{background:var(--c);color:#000}
.info{flex:1}
.title{font-size:1.05rem;color:#fff;margin-bottom:4px;transition:color .18s}
.card:hover .title{color:var(--c)}
.desc{font-size:.74rem;color:#6a6a90}
.tag{padding:3px 12px;border-radius:20px;font-size:.65rem;font-weight:bold;
     border:1px solid var(--c);color:var(--c);background:transparent;letter-spacing:.1em;
     transition:all .18s;flex-shrink:0}
.card:hover .tag{background:var(--c);color:#000}
#status{width:680px;max-width:100%;margin-top:24px;min-height:44px;border-radius:8px;
        display:flex;align-items:center;justify-content:center;font-size:.82rem;
        padding:10px 20px;text-align:center;transition:all .3s}
#status.idle{background:#0d0d26;border:1px solid #2a0050;color:#4a4a6a}
#status.compiling{background:#1a0838;border:1px solid #b400ff;color:#b400ff;animation:pulse 1s infinite}
#status.ok{background:#051a0d;border:1px solid #00ff78;color:#00ff78}
#status.err{background:#1a0505;border:1px solid #ff3c3c;color:#ff3c3c}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.phases{margin-top:36px;font-size:.68rem;color:#2e2e50;text-align:center;line-height:1.9}
.phases span{color:#3a3a60}
.hint{margin-top:10px;font-size:.68rem;color:#2e2e50;letter-spacing:.1em}
</style>
</head>
<body>
<h1>RETROLANG</h1>
<div class="sub">A Retro Arcade Scripting Language &amp; Compiler &nbsp;·&nbsp; CS4031 Spring 2026</div>
<div class="divider"></div>
<div class="prompt">── SELECT A GAME TO COMPILE &amp; PLAY ──</div>

<div class="cards" id="cards"></div>

<div id="status" class="idle">Ready — click a game to compile &amp; launch</div>

<div class="phases">
  <span>COMPILER PHASES</span><br>
  ① Lexer → tokens &nbsp;|&nbsp; ② Parser → AST &nbsp;|&nbsp; ③ Semantic → symbol table<br>
  ④ IR Gen → TAC &nbsp;|&nbsp; ⑤ Optimizer → fold / peephole &nbsp;|&nbsp; ⑥ CodeGen → pygame
</div>
<div class="hint">press 1–5 to select &nbsp;·&nbsp; the game window will open automatically</div>

<script>
const GAMES = __GAMES_JSON__;

function renderCards() {
  const c = document.getElementById('cards');
  GAMES.forEach((g, i) => {
    const div = document.createElement('div');
    div.className = 'card';
    div.style.setProperty('--c', g.color);
    div.style.setProperty('--glow', g.color);
    div.innerHTML = `
      <div class="badge">${i+1}</div>
      <div class="info">
        <div class="title">${g.title}</div>
        <div class="desc">${g.desc}</div>
      </div>
      <div class="tag">${g.tag}</div>`;
    div.addEventListener('click', () => launch(g.id));
    c.appendChild(div);
  });
}

function setStatus(cls, msg) {
  const el = document.getElementById('status');
  el.className = cls;
  el.textContent = msg;
}

let busy = false;
async function launch(id) {
  if (busy) return;
  busy = true;
  setStatus('compiling', '⚙  Compiling through all 6 phases…');
  try {
    const r = await fetch('/launch?id=' + id);
    const j = await r.json();
    if (j.ok) {
      setStatus('ok', '✓  Compiled successfully — game window is launching! (check your Dock)');
    } else {
      setStatus('err', '✗  ' + j.error);
    }
  } catch(e) {
    setStatus('err', '✗  Server error: ' + e.message);
  }
  setTimeout(() => { setStatus('idle', 'Ready — click a game to compile & launch'); busy = false; }, 4000);
}

document.addEventListener('keydown', e => {
  const n = parseInt(e.key);
  if (n >= 1 && n <= GAMES.length) launch(GAMES[n-1].id);
});

renderCards();
</script>
</body>
</html>
""".replace("__GAMES_JSON__", json.dumps(GAMES))


def compile_and_launch(game_id):
    game = next((g for g in GAMES if g["id"] == game_id), None)
    if not game:
        return False, "Unknown game id"
    abs_path = os.path.join(HERE, game["file"])
    try:
        with open(abs_path) as f:
            source = f.read()
        tokens  = tokenize(source)
        ast     = parse(tokens, source)
        _       = analyze(ast, source)
        ir, tac = lower(ast)
        ir, tac = optimize(ir, tac)
        py_src  = generate(ir)
    except RetroError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected compiler error: {e}"

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     dir=tempfile.gettempdir()) as f:
        f.write(py_src)
        path = f.name

    env = os.environ.copy()
    env["SDL_VIDEO_MAC_FULLSCREEN_SPACES"] = "0"
    env.pop("SDL_VIDEODRIVER", None)

    # Launch the game as a completely detached child process
    subprocess.Popen(
        [sys.executable, path],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,   # detach from our process group
    )
    return True, "ok"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # silence request logs

    def _send(self, code, ctype, body):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, "text/html; charset=utf-8", HTML)
        elif parsed.path == "/launch":
            qs = parse_qs(parsed.query)
            gid = qs.get("id", [""])[0]
            ok, msg = compile_and_launch(gid)
            self._send(200, "application/json", json.dumps({"ok": ok, "error": msg}))
        else:
            self._send(404, "text/plain", "not found")


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\n  RetroLang Launcher  →  {url}")
    print("  Opening browser…  (Ctrl+C to quit)\n")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Launcher stopped.")


if __name__ == "__main__":
    main()

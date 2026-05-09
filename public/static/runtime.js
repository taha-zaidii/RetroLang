/* ===================================================================
   RetroLang in-browser runtime — shared base
   -------------------------------------------------------------------
   Mirrors the constants and helpers from src/codegen.py so a .retro
   program produces identical gameplay in the browser as it does in
   pygame on the desktop. Game-specific logic lives in tetris.js and
   snake.js.
   =================================================================== */

window.Retro = window.Retro || {};

// ---- KEYMAP — matches PYGAME_KEY_MAP in src/codegen.py ----
Retro.KEYMAP = {
  KEY_LEFT:   'ArrowLeft',
  KEY_RIGHT:  'ArrowRight',
  KEY_UP:     'ArrowUp',
  KEY_DOWN:   'ArrowDown',
  KEY_SPACE:  ' ',
  KEY_RETURN: 'Enter',
  KEY_ESCAPE: 'Escape',
  KEY_P: 'p',
  KEY_Q: 'q',
  KEY_R: 'r',
  KEY_W: 'w',
  KEY_A: 'a',
  KEY_S: 's',
  KEY_D: 'd',
};

// Pretty key labels for HUD
Retro.KEY_LABELS = {
  KEY_LEFT:   '←',
  KEY_RIGHT:  '→',
  KEY_UP:     '↑',
  KEY_DOWN:   '↓',
  KEY_SPACE:  'SPACE',
  KEY_RETURN: 'ENTER',
  KEY_ESCAPE: 'ESC',
  KEY_P: 'P',  KEY_Q: 'Q',  KEY_R: 'R',
  KEY_W: 'W',  KEY_A: 'A',  KEY_S: 'S', KEY_D: 'D',
};

// Theme palettes — copied verbatim from THEME_PALETTES in src/codegen.py
Retro.THEME_PALETTES = {
  NEON:      { text: '#FFFFFF', grid: '#1a1a2e', accent: '#FF00FF' },
  CRT_GREEN: { text: '#33FF33', grid: '#003300', accent: '#33FF33' },
  AMBER:     { text: '#FFB000', grid: '#332200', accent: '#FFB000' },
  MONO:      { text: '#DDDDDD', grid: '#222222', accent: '#FFFFFF' },
  DEFAULT:   { text: '#FFFFFF', grid: '#222222', accent: '#888888' },
};

Retro.HUD_HEIGHT = 64;

Retro.hexToRgb = function (hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};
Retro.toCss = function (rgb) { return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`; };

/* -------------------------------------------------------------------
   Engine — abstract base for both game modes.
   -------------------------------------------------------------------
   Subclass overrides:
     reset()         -> initial state object
     onKey(key)      -> handle keydown (key is normalized event.key)
     update(dt, st)  -> advance simulation by dt ms
     render(ctx, st) -> draw
     hudFields(st)   -> { score, ...mode-specific }
   ------------------------------------------------------------------- */

Retro.Engine = class {
  constructor(canvas, ir, opts = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.ir = ir;
    this.palette = Retro.THEME_PALETTES[ir.theme] || Retro.THEME_PALETTES.DEFAULT;
    this.bg     = Retro.toCss(Retro.hexToRgb(ir.background));
    this.text   = Retro.toCss(Retro.hexToRgb(this.palette.text));
    this.grid   = Retro.toCss(Retro.hexToRgb(this.palette.grid));
    this.accent = Retro.toCss(Retro.hexToRgb(this.palette.accent));

    this.cell = ir.block_size;
    this.gridW = ir.grid_w;
    this.gridH = ir.grid_h;
    this.windowW = this.gridW * this.cell;
    this.windowH = this.gridH * this.cell + Retro.HUD_HEIGHT;

    canvas.width  = this.windowW;
    canvas.height = this.windowH;
    canvas.style.maxHeight = '78vh';

    // action -> KEY_X  (from .retro source)
    this.controls = ir.controls || {};
    // KEY_X -> action  (reverse map for fast lookup)
    this.actionFor = {};
    for (const [action, keyName] of Object.entries(this.controls)) {
      this.actionFor[keyName] = action;
    }

    this.onHud  = opts.onHud  || (() => {});
    this.onOver = opts.onOver || (() => {});
    this.sfx    = opts.sfx    || null;

    this._raf = null;
    this._last = 0;
    this._heldKeys = new Set();
    this._kbBound = this._kbHandler.bind(this);
    this._keyUpBound = (e) => this._heldKeys.delete(e.key);
    this.state = null;
  }

  // The active game-mode subclass should override these.
  reset()         { return {}; }
  onKey(_key)     {}
  update(_dt, _s) {}
  render(_ctx, _s){}
  hudFields(_s)   { return { score: 0 }; }

  start() {
    this.state = this.reset();
    this._emitHud();
    window.addEventListener('keydown', this._kbBound, { passive: false });
    window.addEventListener('keyup',   this._keyUpBound);
    this._last = performance.now();
    const tick = (now) => {
      const dt = Math.min(60, now - this._last);  // clamp dt to avoid huge jumps
      this._last = now;
      if (!this.state.paused && !this.state.game_over) {
        this.update(dt, this.state);
      }
      this.render(this.ctx, this.state);
      this._emitHud();
      this._raf = requestAnimationFrame(tick);
    };
    this._raf = requestAnimationFrame(tick);
  }

  stop() {
    if (this._raf) cancelAnimationFrame(this._raf);
    window.removeEventListener('keydown', this._kbBound);
    window.removeEventListener('keyup',   this._keyUpBound);
    this._raf = null;
  }

  restart() {
    this.state = this.reset();
    this._emitHud();
  }

  // map a JS event.key to a RetroLang KEY_* identifier
  _normalize(jsKey) {
    if (!jsKey) return null;
    if (jsKey === ' ' || jsKey === 'Spacebar') return 'KEY_SPACE';
    const direct = {
      ArrowLeft:'KEY_LEFT', ArrowRight:'KEY_RIGHT',
      ArrowUp:'KEY_UP', ArrowDown:'KEY_DOWN',
      Enter:'KEY_RETURN', Escape:'KEY_ESCAPE',
    }[jsKey];
    if (direct) return direct;
    const lc = jsKey.length === 1 ? jsKey.toLowerCase() : jsKey;
    const single = { p:'KEY_P', q:'KEY_Q', r:'KEY_R',
                     w:'KEY_W', a:'KEY_A', s:'KEY_S', d:'KEY_D' }[lc];
    return single || null;
  }

  _kbHandler(e) {
    const retroKey = this._normalize(e.key);
    if (!retroKey) return;
    const action = this.actionFor[retroKey];
    if (!action) return;
    // Always swallow keys that the game has bound — including arrows/space
    // so the page doesn't scroll while playing.
    e.preventDefault();
    if (e.repeat && action !== 'soft_drop' && action !== 'move_left' && action !== 'move_right') return;
    this.onKey(retroKey, action, e);
  }

  // Subclasses call this whenever stats change (or every frame).
  _emitHud() { this.onHud(this.hudFields(this.state)); }

  /* -------- shared draw helpers (HUD + block) -------- */
  drawBlock(x, y, color) {
    const c = this.ctx;
    const px = x * this.cell;
    const py = y * this.cell + Retro.HUD_HEIGHT;
    c.fillStyle = color;
    c.fillRect(px, py, this.cell, this.cell);
    c.strokeStyle = this.grid;
    c.lineWidth = 1;
    c.strokeRect(px + 0.5, py + 0.5, this.cell - 1, this.cell - 1);
    // subtle bevel
    c.fillStyle = 'rgba(255,255,255,.12)';
    c.fillRect(px, py, this.cell, 2);
    c.fillStyle = 'rgba(0,0,0,.20)';
    c.fillRect(px, py + this.cell - 2, this.cell, 2);
  }

  drawHUD(line1, line2) {
    const c = this.ctx;
    c.fillStyle = '#000';
    c.fillRect(0, 0, this.windowW, Retro.HUD_HEIGHT);
    c.fillStyle = this.text;
    c.font = 'bold 16px "Share Tech Mono", "Courier New", monospace';
    c.textBaseline = 'top';
    c.fillText(line1, 10, 10);
    c.fillStyle = this.accent;
    c.fillText(line2, 10, 32);
  }

  drawGameOver() {
    const c = this.ctx;
    c.fillStyle = 'rgba(0,0,0,.65)';
    c.fillRect(0, 0, this.windowW, this.windowH);
    c.fillStyle = this.accent;
    c.font = 'bold 18px "Share Tech Mono", "Courier New", monospace';
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.fillText('GAME OVER — press R to restart, Q to quit',
               this.windowW / 2, this.windowH / 2);
    c.textAlign = 'start';
  }
};

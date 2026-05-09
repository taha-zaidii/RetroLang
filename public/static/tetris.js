/* ===================================================================
   Tetris runtime — direct port of _gen_tetris in src/codegen.py
   -------------------------------------------------------------------
   Parity rules, deliberately preserved:
     • new_piece() uses random.choice(PIECES) and centers on x = GRID_W//2 - len(shape[0])//2
     • rotate_shape == zip(*shape[::-1])  (i.e. transpose-after-reverse, 90° CW)
     • drop_interval = max(60, GRAVITY_MS * 0.85^(level-1))
     • bonus_tetris is added on a 4-line clear in the same tick
     • game_over_conditions["on_top_collision"] freezes state when the
       newly spawned piece collides on its first frame
   =================================================================== */

Retro.TetrisEngine = class extends Retro.Engine {
  constructor(canvas, ir, opts) {
    super(canvas, ir, opts);
    this.GRAVITY_MS      = ir.gravity_speed;
    this.SPEEDUP_LINES   = ir.speedup_every;
    this.SCORE_PER_LINE  = ir.score_per_line;
    this.BONUS_TETRIS    = ir.bonus_tetris;
    this.GAME_OVER_CONDS = ir.game_over_conditions || [];

    // Pieces — convert color hex once.
    this.PIECES = (ir.pieces || []).map(p => ({
      name:  p.name,
      shape: p.shape.map(row => row.slice()),
      color: Retro.toCss(Retro.hexToRgb(p.color)),
    }));
  }

  reset() {
    return {
      board: Array.from({ length: this.gridH }, () => new Array(this.gridW).fill(null)),
      piece: this._newPiece(),
      score: 0,
      lines: 0,
      level: 1,
      drop_timer: 0,
      drop_interval: this.GRAVITY_MS,
      paused: false,
      game_over: false,
    };
  }

  _newPiece() {
    const proto = this.PIECES[Math.floor(Math.random() * this.PIECES.length)];
    const shape = proto.shape.map(row => row.slice());
    return {
      name:  proto.name,
      shape: shape,
      color: proto.color,
      x: Math.floor(this.gridW / 2) - Math.floor(shape[0].length / 2),
      y: 0,
    };
  }

  // mirror of: rotate_shape(shape) -> [list(row) for row in zip(*shape[::-1])]
  _rotate(shape) {
    const h = shape.length, w = shape[0].length;
    const out = Array.from({ length: w }, () => new Array(h));
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        out[c][h - 1 - r] = shape[r][c];
      }
    }
    return out;
  }

  // mirror of: collides(board, piece, dx=0, dy=0, shape=None)
  _collides(board, piece, dx = 0, dy = 0, shape = null) {
    const sh = shape || piece.shape;
    for (let r = 0; r < sh.length; r++) {
      for (let c = 0; c < sh[r].length; c++) {
        if (!sh[r][c]) continue;
        const x = piece.x + c + dx;
        const y = piece.y + r + dy;
        if (x < 0 || x >= this.gridW || y >= this.gridH) return true;
        if (y >= 0 && board[y][x] !== null) return true;
      }
    }
    return false;
  }

  _lock(board, piece) {
    for (let r = 0; r < piece.shape.length; r++) {
      for (let c = 0; c < piece.shape[r].length; c++) {
        if (!piece.shape[r][c]) continue;
        const y = piece.y + r, x = piece.x + c;
        if (y >= 0 && y < this.gridH && x >= 0 && x < this.gridW) {
          board[y][x] = piece.color;
        }
      }
    }
  }

  // mirror of: clear_lines — a row clears when ALL cells are non-null.
  _clearLines(board) {
    const kept = board.filter(row => row.some(cell => cell === null));
    const cleared = this.gridH - kept.length;
    while (kept.length < this.gridH) kept.unshift(new Array(this.gridW).fill(null));
    return [kept, cleared];
  }

  onKey(retroKey, action) {
    const st = this.state;
    if (action === 'quit')    { this.onOver({ kind: 'quit', score: st.score }); return; }
    if (action === 'restart') { this.restart(); return; }
    if (st.game_over) {
      // Match the codegen: on game-over only R/Q work.
      if (retroKey === 'KEY_R') this.restart();
      return;
    }
    if (action === 'pause')   { st.paused = !st.paused; if (this.sfx) this.sfx.beep(220, .04); return; }
    if (st.paused) return;

    const p = st.piece;
    if (action === 'move_left'  && !this._collides(st.board, p, -1)) { p.x--; this.sfx?.tick(); }
    else if (action === 'move_right' && !this._collides(st.board, p,  1)) { p.x++; this.sfx?.tick(); }
    else if (action === 'soft_drop'  && !this._collides(st.board, p, 0, 1)) { p.y++; }
    else if (action === 'rotate') {
      const rot = this._rotate(p.shape);
      if (!this._collides(st.board, p, 0, 0, rot)) { p.shape = rot; this.sfx?.beep(660, .03); }
    }
    else if (action === 'hard_drop') {
      while (!this._collides(st.board, p, 0, 1)) p.y++;
      st.drop_timer = st.drop_interval;  // force lock on next tick
      this.sfx?.beep(180, .06, 'square');
    }
  }

  update(dt, st) {
    st.drop_timer += dt;
    if (st.drop_timer < st.drop_interval) return;
    st.drop_timer = 0;
    const p = st.piece;
    if (this._collides(st.board, p, 0, 1)) {
      this._lock(st.board, p);
      const [board2, cleared] = this._clearLines(st.board);
      st.board = board2;
      if (cleared) {
        let gained = this.SCORE_PER_LINE * cleared;
        if (cleared === 4) gained += this.BONUS_TETRIS;
        st.score += gained;
        st.lines += cleared;
        const newLevel = 1 + Math.floor(st.lines / Math.max(1, this.SPEEDUP_LINES));
        if (newLevel > st.level) {
          st.level = newLevel;
          st.drop_interval = Math.max(60, Math.floor(this.GRAVITY_MS * Math.pow(0.85, newLevel - 1)));
          this.sfx?.chord([523, 659, 784], .12);
        } else {
          this.sfx?.beep(440, .07);
        }
      } else {
        this.sfx?.beep(140, .03);
      }
      st.piece = this._newPiece();
      if (this.GAME_OVER_CONDS.includes('on_top_collision') && this._collides(st.board, st.piece)) {
        st.game_over = true;
        this.sfx?.gameOver();
        this.onOver({ kind: 'gameover', score: st.score });
      }
    } else {
      p.y++;
    }
  }

  render(ctx, st) {
    ctx.fillStyle = this.bg;
    ctx.fillRect(0, 0, this.windowW, this.windowH);

    // playfield grid (subtle)
    ctx.strokeStyle = this.grid;
    ctx.lineWidth = 1;
    for (let i = 1; i < this.gridW; i++) {
      const x = i * this.cell + 0.5;
      ctx.beginPath();
      ctx.moveTo(x, Retro.HUD_HEIGHT);
      ctx.lineTo(x, this.windowH);
      ctx.stroke();
    }
    for (let i = 1; i < this.gridH; i++) {
      const y = i * this.cell + Retro.HUD_HEIGHT + 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.windowW, y);
      ctx.stroke();
    }

    // locked cells
    for (let y = 0; y < this.gridH; y++) {
      for (let x = 0; x < this.gridW; x++) {
        const cell = st.board[y][x];
        if (cell !== null) this.drawBlock(x, y, cell);
      }
    }

    // active piece
    if (!st.game_over) {
      const p = st.piece;
      for (let r = 0; r < p.shape.length; r++) {
        for (let c = 0; c < p.shape[r].length; c++) {
          if (p.shape[r][c]) this.drawBlock(p.x + c, p.y + r, p.color);
        }
      }
    }

    // HUD line + game-over overlay
    this.drawHUD(
      `SCORE ${st.score}   LINES ${st.lines}   LEVEL ${st.level}`,
      this.ir.name + (st.paused ? '  — PAUSED' : '')
    );
    if (st.game_over) this.drawGameOver();
  }

  hudFields(st) {
    if (!st) return { score: 0, lines: 0, level: 1, mode: 'tetris' };
    return { score: st.score, lines: st.lines, level: st.level, mode: 'tetris' };
  }
};

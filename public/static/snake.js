/* ===================================================================
   Snake runtime — direct port of _gen_snake in src/codegen.py
   -------------------------------------------------------------------
   Parity rules, deliberately preserved:
     • initial snake is [(cx-i, cy) for i in range(START_LENGTH)]
     • next_dir is queued; reversal of the current dir is rejected
       (vec[0]+dir[0], vec[1]+dir[1]) != (0,0)
     • WRAP_EDGES wraps coordinates, otherwise on_wall_collision (if in
       game_over_conditions) ends the game
     • on_self_collision likewise ends the game on that condition
     • food respawn never picks a cell already occupied by snake or food
   =================================================================== */

Retro.SnakeEngine = class extends Retro.Engine {
  constructor(canvas, ir, opts) {
    super(canvas, ir, opts);
    this.START_LENGTH    = ir.start_length;
    this.FOOD_COUNT      = ir.food_count;
    this.WRAP_EDGES      = ir.wrap_edges;
    this.SPEED_MS        = ir.snake_speed;
    this.SCORE_PER_FOOD  = ir.score_per_food;
    this.GAME_OVER_CONDS = ir.game_over_conditions || [];
    this.SNAKE_COLOR     = this.accent;
    this.FOOD_COLOR      = this.text;
    this.DIRS = {
      move_up:    [0, -1],
      move_down:  [0,  1],
      move_left:  [-1, 0],
      move_right: [1,  0],
    };
  }

  reset() {
    const cx = Math.floor(this.gridW / 2);
    const cy = Math.floor(this.gridH / 2);
    const snake = [];
    for (let i = 0; i < this.START_LENGTH; i++) snake.push([cx - i, cy]);
    const foods = [];
    for (let i = 0; i < this.FOOD_COUNT; i++) foods.push(this._spawnFood(snake, foods));
    return {
      snake,
      foods,
      dir:      [1, 0],
      next_dir: [1, 0],
      score:    0,
      tick:     0,
      paused:   false,
      game_over: false,
    };
  }

  _spawnFood(snake, foods) {
    while (true) {
      const x = Math.floor(Math.random() * this.gridW);
      const y = Math.floor(Math.random() * this.gridH);
      const inSnake = snake.some(s => s[0] === x && s[1] === y);
      const inFood  = foods.some(f => f[0] === x && f[1] === y);
      if (!inSnake && !inFood) return [x, y];
    }
  }

  onKey(retroKey, action) {
    const st = this.state;
    if (action === 'quit')    { this.onOver({ kind: 'quit', score: st.score }); return; }
    if (action === 'restart') { this.restart(); return; }
    if (st.game_over) {
      if (retroKey === 'KEY_R') this.restart();
      return;
    }
    if (action === 'pause')   { st.paused = !st.paused; this.sfx?.beep(220, .04); return; }
    if (st.paused) return;

    const vec = this.DIRS[action];
    if (!vec) return;
    // disallow direct reversal
    if ((vec[0] + st.dir[0]) !== 0 || (vec[1] + st.dir[1]) !== 0) {
      st.next_dir = vec;
      this.sfx?.tick();
    }
  }

  update(dt, st) {
    st.tick += dt;
    if (st.tick < this.SPEED_MS) return;
    st.tick = 0;
    st.dir = st.next_dir;
    const [hx, hy] = st.snake[0];
    const [dx, dy] = st.dir;
    let nx = hx + dx, ny = hy + dy;

    if (this.WRAP_EDGES) {
      nx = ((nx % this.gridW) + this.gridW) % this.gridW;
      ny = ((ny % this.gridH) + this.gridH) % this.gridH;
    } else if (nx < 0 || nx >= this.gridW || ny < 0 || ny >= this.gridH) {
      if (this.GAME_OVER_CONDS.includes('on_wall_collision')) {
        st.game_over = true;
        this.sfx?.gameOver();
        this.onOver({ kind: 'gameover', score: st.score });
        return;
      }
    }

    const collidesSelf = st.snake.some(s => s[0] === nx && s[1] === ny);
    if (collidesSelf && this.GAME_OVER_CONDS.includes('on_self_collision')) {
      st.game_over = true;
      this.sfx?.gameOver();
      this.onOver({ kind: 'gameover', score: st.score });
      return;
    }

    st.snake.unshift([nx, ny]);
    const foodIdx = st.foods.findIndex(f => f[0] === nx && f[1] === ny);
    if (foodIdx !== -1) {
      st.foods.splice(foodIdx, 1);
      st.foods.push(this._spawnFood(st.snake, st.foods));
      st.score += this.SCORE_PER_FOOD;
      this.sfx?.beep(880, .08);
    } else {
      st.snake.pop();
    }
  }

  render(ctx, st) {
    ctx.fillStyle = this.bg;
    ctx.fillRect(0, 0, this.windowW, this.windowH);

    // Subtle grid for CRT vibe
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

    for (const [fx, fy] of st.foods) this.drawBlock(fx, fy, this.FOOD_COLOR);
    for (const [sx, sy] of st.snake) this.drawBlock(sx, sy, this.SNAKE_COLOR);

    this.drawHUD(
      `SCORE ${st.score}   LENGTH ${st.snake.length}`,
      this.ir.name + (st.paused ? '  — PAUSED' : '')
    );
    if (st.game_over) this.drawGameOver();
  }

  hudFields(st) {
    if (!st) return { score: 0, length: this.START_LENGTH, mode: 'snake' };
    return { score: st.score, length: st.snake.length, mode: 'snake' };
  }
};

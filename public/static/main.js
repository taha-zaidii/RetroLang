/* ===================================================================
   RetroLang Arcade — main orchestration
   -------------------------------------------------------------------
   Wires the boot screen, lobby, compile-trace animation, and game
   runtime together. Talks to /api/compile and /api/examples.
   =================================================================== */

(function () {
  'use strict';

  /* ---------- DOM helpers ---------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[ch]);
  }

  /* ---------- App state ---------- */
  const state = {
    examples: [],
    activeEngine: null,
    lastCompiled: null,    // { id, ir, source, trace }
    sfxOn: true,
  };

  /* ============================ BOOT ============================ */

  const bootMessages = [
    '> POWER ON …',
    '> RETROLANG BIOS v1.0  (FAST-NU 2026)',
    '> initializing 6-phase compiler pipeline …',
    '> [01] LEXER     ready',
    '> [02] PARSER    ready',
    '> [03] SEMANTIC  ready',
    '> [04] IR        ready',
    '> [05] OPTIMIZER ready',
    '> [06] CODEGEN   ready',
    '> all systems nominal.',
  ];
  function runBoot() {
    const log = $('#boot-log');
    let i = 0;
    function next() {
      if (i >= bootMessages.length) return;
      const span = document.createElement('span');
      span.textContent = bootMessages[i];
      span.style.animationDelay = (i * 0.04) + 's';
      log.appendChild(span);
      i++;
      setTimeout(next, 80);
    }
    next();
  }

  function dismissBoot() {
    const boot = $('#boot');
    const cab  = $('#cab');
    if (!boot.classList.contains('active')) return;
    Retro.SFX.coin();
    boot.style.transition = 'opacity .35s ease-out';
    boot.style.opacity = 0;
    setTimeout(() => {
      boot.classList.remove('active');
      cab.classList.remove('hidden');
      Retro.SFX.boot();
    }, 350);
  }

  /* ============================ LOBBY ============================ */

  async function loadExamples() {
    try {
      const res = await fetch('/api/examples', { headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      state.examples = await res.json();
    } catch (e) {
      // Fallback: show error card
      state.examples = [];
      showToast(
        'Could not reach /api/examples — the live deployment may not be ready yet.\n' +
        'If you\'re testing locally, run `vercel dev` instead of a plain static server.',
      );
    }
    renderCards();
  }

  function renderCards() {
    const cards = $('#cards');
    cards.innerHTML = '';
    state.examples.forEach((g, i) => {
      const div = document.createElement('div');
      div.className = 'card';
      div.style.setProperty('--c', g.color);
      div.tabIndex = 0;
      div.setAttribute('role', 'button');
      div.setAttribute('aria-label', `Compile and play ${g.title}`);
      div.innerHTML = `
        <div class="card-row">
          <div class="card-badge">${i + 1}</div>
          <div class="card-tag">${escapeHtml(g.tag)}</div>
        </div>
        <div class="card-title">${escapeHtml(g.title)}</div>
        <div class="card-desc">${escapeHtml(g.desc)}</div>
        <div class="card-cta">PLAY</div>
      `;
      div.addEventListener('click', () => launchExample(g));
      div.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); launchExample(g); }
      });
      cards.appendChild(div);
    });
  }

  /* ============================ COMPILE ============================ */

  let compileAbort = null;

  async function launchExample(game) {
    Retro.SFX.beep(660, .04);
    showScreen('compile');
    setMarquee('— COMPILING —');
    await runCompile({
      id:    game.id,
      title: game.title,
      tag:   game.tag,
      color: game.color,
      file:  game.file,
      source: game.source,
    });
  }

  async function launchOwnSource() {
    const source = $('#own-source').value.trim();
    if (!source) { showToast('Write some .retro code first.'); return; }
    Retro.SFX.beep(660, .04);
    showScreen('compile');
    setMarquee('— COMPILING (CUSTOM) —');
    await runCompile({
      id: 'custom', title: 'Your Program', tag: 'CUSTOM',
      color: '#ffd700', file: 'custom.retro', source,
    });
  }

  async function runCompile(payload) {
    const trace = $('#trace');
    trace.innerHTML = '';
    setStatus('Initialising compiler…');

    if (compileAbort) compileAbort.abort();
    compileAbort = new AbortController();

    // Phase 1 — show lexer running
    await typeLine(trace, 'PHASE 1 ▸ Lexical Analysis     ', 'ph');
    await wait(180);

    // Talk to /api/compile
    let result;
    try {
      const res = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ source: payload.source }),
        signal: compileAbort.signal,
      });
      result = await res.json();
    } catch (e) {
      if (e.name === 'AbortError') return;
      await typeLine(trace, 'NETWORK ERROR — ' + e.message, 'err');
      setStatus('Compile aborted');
      return;
    }

    if (!result.ok) {
      await typeLine(trace, '✗ ' + result.phase + ' error', 'err');
      const lines = (result.message || 'Unknown error').split('\n');
      for (const ln of lines) await typeLine(trace, '  ' + ln, 'dim');
      setStatus('Compilation failed in ' + result.phase + ' phase');
      showToast('<b>' + escapeHtml(result.phase) + ' error</b>\n' + escapeHtml(result.message));
      return;
    }

    const { ir, trace: tr } = result;

    await typeLine(trace, `✓ ${tr.tokens} tokens scanned`, 'ok');
    await wait(120);
    await typeLine(trace, 'PHASE 2 ▸ Syntax Analysis      ', 'ph');
    await wait(180);
    await typeLine(trace, `✓ AST built · ${tr.ast_nodes} nodes`, 'ok');
    await wait(120);
    await typeLine(trace, 'PHASE 3 ▸ Semantic Analysis    ', 'ph');
    await wait(180);
    await typeLine(trace, `✓ symbol table populated · mode=${ir.mode}`, 'ok');
    await wait(120);
    await typeLine(trace, 'PHASE 4 ▸ IR Generation        ', 'ph');
    await wait(180);
    await typeLine(trace, `✓ ${tr.tac_before.length} TAC quads emitted`, 'ok');
    await wait(120);
    await typeLine(trace, 'PHASE 5 ▸ Optimization         ', 'ph');
    await wait(180);
    if (tr.optimization_log.length) {
      for (const ln of tr.optimization_log) {
        await typeLine(trace, '  · ' + ln, 'dim');
      }
    } else {
      await typeLine(trace, '  · no rewrites triggered', 'dim');
    }
    await typeLine(trace, `✓ ${tr.tac_after.length} TAC quads after opt`, 'ok');
    await wait(120);
    await typeLine(trace, 'PHASE 6 ▸ Code Generation      ', 'ph');
    await wait(220);
    await typeLine(trace, `✓ runtime ready — launching ${escapeHtml(ir.name)}`, 'ok');
    await wait(380);

    state.lastCompiled = {
      id: payload.id, title: payload.title, tag: payload.tag, color: payload.color,
      ir, source: payload.source, trace: tr,
    };
    mountGame(ir, payload);
  }

  function setStatus(msg) { $('#compile-status').textContent = msg; }

  function typeLine(host, text, cls) {
    return new Promise(resolve => {
      const div = document.createElement('div');
      if (cls) div.className = cls;
      host.appendChild(div);
      let i = 0;
      const speed = Math.max(8, Math.min(28, Math.floor(900 / Math.max(1, text.length))));
      const tickAudio = () => Retro.SFX.tick();
      function step() {
        div.textContent = text.slice(0, i);
        i += 1;
        if (i % 4 === 0) tickAudio();
        if (i <= text.length) setTimeout(step, speed);
        else { host.scrollTop = host.scrollHeight; resolve(); }
      }
      step();
    });
  }
  function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

  /* ============================ PLAY ============================ */

  function mountGame(ir, payload) {
    showScreen('play');
    setMarquee(`RETROLANG · ${ir.name.toUpperCase()}`);

    if (state.activeEngine) { state.activeEngine.stop(); state.activeEngine = null; }
    const canvas = $('#canvas');
    const Engine = ir.mode === 'snake' ? Retro.SnakeEngine : Retro.TetrisEngine;
    const engine = new Engine(canvas, ir, {
      onHud:  updateHud,
      onOver: () => {},
      sfx:    Retro.SFX,
    });
    state.activeEngine = engine;
    engine.start();
    canvas.focus();

    renderControls(ir);
    $('#src-meta').innerHTML =
      `<b>${escapeHtml(ir.name)}</b><br>${escapeHtml(payload.file || '')}<br>` +
      `mode=<b>${ir.mode}</b> · grid ${ir.grid_w}×${ir.grid_h} · theme ${ir.theme}`;

    // mode-specific HUD rows
    const isSnake = ir.mode === 'snake';
    $('#hud-row2').hidden = isSnake;        // LINES
    $('#hud-row3').hidden = isSnake;        // LEVEL
    $('#hud-row-len').hidden = !isSnake;    // LENGTH
  }

  function updateHud(f) {
    if (f.mode === 'snake') {
      $('#hud-score').textContent = f.score;
      $('#hud-len').textContent   = f.length;
    } else {
      $('#hud-score').textContent = f.score;
      $('#hud-lines').textContent = f.lines;
      $('#hud-level').textContent = f.level;
    }
  }

  function renderControls(ir) {
    const ul = $('#hud-keys');
    ul.innerHTML = '';
    const ACTION_LABEL = {
      move_left:'Move L', move_right:'Move R', move_up:'Up', move_down:'Down',
      rotate:'Rotate', soft_drop:'Soft drop', hard_drop:'Hard drop',
      pause:'Pause', restart:'Restart', quit:'Quit',
    };
    for (const [action, key] of Object.entries(ir.controls || {})) {
      const li = document.createElement('li');
      const label = ACTION_LABEL[action] || action;
      const keyLabel = Retro.KEY_LABELS[key] || key;
      li.innerHTML = `<b>${escapeHtml(label)}</b><kbd>${escapeHtml(keyLabel)}</kbd>`;
      ul.appendChild(li);
    }
  }

  /* ============================ Misc UI ============================ */

  function setMarquee(t) { const el = $('#marquee'); if (el) el.textContent = t; }

  function showScreen(name) {
    for (const id of ['lobby', 'compile', 'play']) {
      const el = document.getElementById(id);
      if (!el) continue;
      el.hidden = (id !== name);
      el.classList.toggle('active', id === name);
    }
    if (name !== 'play' && state.activeEngine) {
      state.activeEngine.stop(); state.activeEngine = null;
    }
    if (name === 'lobby') setMarquee('RETROLANG · ARCADE');
  }

  function showToast(html, kind) {
    const t = $('#toast');
    t.innerHTML = html;
    t.hidden = false;
    if (kind) t.dataset.kind = kind;
    clearTimeout(showToast._h);
    showToast._h = setTimeout(() => { t.hidden = true; }, 5500);
  }

  function showModal(title, body) {
    $('#modal-title').textContent = title;
    $('#modal-body').textContent  = body;
    $('#modal').hidden = false;
  }

  /* ============================ Wire-up ============================ */

  document.addEventListener('DOMContentLoaded', () => {
    runBoot();
    loadExamples();

    /* Boot dismiss */
    $('#insert-coin').addEventListener('click', dismissBoot);
    document.addEventListener('keydown', function bootKey(e) {
      if ($('#boot').classList.contains('active')) {
        // Any key dismisses boot, except modifier-only presses
        if (e.key === 'Shift' || e.key === 'Control' || e.key === 'Alt' || e.key === 'Meta') return;
        dismissBoot();
        document.removeEventListener('keydown', bootKey);
      }
    });

    /* SFX toggle */
    const sfxBtn = $('#sfx-toggle');
    sfxBtn.addEventListener('click', () => {
      state.sfxOn = !state.sfxOn;
      Retro.SFX.enabled = state.sfxOn;
      sfxBtn.textContent = 'SFX: ' + (state.sfxOn ? 'ON' : 'OFF');
      sfxBtn.setAttribute('aria-pressed', state.sfxOn);
      if (state.sfxOn) Retro.SFX.beep(700, .05);
    });

    /* Number-key game launch from lobby */
    document.addEventListener('keydown', e => {
      if ($('#boot').classList.contains('active')) return;
      if (e.target && (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT')) return;
      const isLobbyVisible = !document.getElementById('lobby').hidden;
      if (!isLobbyVisible) return;
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= state.examples.length) {
        launchExample(state.examples[n - 1]);
      }
    });

    /* Custom-source button */
    $('#own-launch').addEventListener('click', launchOwnSource);

    /* Compile cancel */
    $('#compile-cancel').addEventListener('click', () => {
      if (compileAbort) compileAbort.abort();
      showScreen('lobby');
    });

    /* Play screen — back & restart */
    $('#back-btn').addEventListener('click', () => {
      if (state.activeEngine) { state.activeEngine.stop(); state.activeEngine = null; }
      showScreen('lobby');
    });
    $('#restart-btn').addEventListener('click', () => {
      if (state.activeEngine) state.activeEngine.restart();
      Retro.SFX.beep(550, .05);
    });
    $('#show-source').addEventListener('click', () => {
      if (!state.lastCompiled) return;
      showModal(state.lastCompiled.title + '  —  .retro source',
                state.lastCompiled.source || '(no source)');
    });
    $('#show-trace').addEventListener('click', () => {
      if (!state.lastCompiled) return;
      const t = state.lastCompiled.trace;
      const lines = [
        '====== PHASE TRACE ======',
        '',
        `Phase 1  Lexer     · ${t.tokens} tokens`,
        `Phase 2  Parser    · ${t.ast_nodes} AST nodes`,
        `Phase 3  Semantic  · ok`,
        `Phase 4  IR        · ${t.tac_before.length} quads`,
        `Phase 5  Optimizer · ${t.tac_after.length} quads`,
        ...(t.optimization_log.length
            ? t.optimization_log.map(l => '            · ' + l)
            : ['            · no rewrites triggered']),
        `Phase 6  Codegen   · runtime mounted`,
        '',
        '------ TAC (after optimization) ------',
        ...t.tac_after.map((q, i) =>
          `${String(i).padStart(3)}: (${String(q[0]).padEnd(10)}, ${
            JSON.stringify(q[1] ?? null)}, ${JSON.stringify(q[2] ?? null)}, ${JSON.stringify(q[3] ?? null)})`),
      ];
      showModal(state.lastCompiled.title + '  —  Compiler trace', lines.join('\n'));
    });

    $('#modal-close').addEventListener('click', () => { $('#modal').hidden = true; });
    $('#modal').addEventListener('click', e => {
      if (e.target.id === 'modal') $('#modal').hidden = true;
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !$('#modal').hidden) $('#modal').hidden = true;
    });

    showScreen('lobby');
  });

})();

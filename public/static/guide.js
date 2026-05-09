/* ===================================================================
   RetroLang Player's Manual
   -------------------------------------------------------------------
   A 7-page interactive manual rendered as a CRT cabinet overlay.
     Page 1  WELCOME              what RetroLang is
     Page 2  QUICK START          three-step getting-started flow
     Page 3  THE COMPILER         the six phases (with live phase demo)
     Page 4  WRITE YOUR OWN       syntax-highlighted language tour
     Page 5  CONTROLS             keymap reference (Tetris + Snake + UI)
     Page 6  PRO TIPS             non-obvious things the user can try
     Page 7  CREDITS              authors / course / license
   Navigation:
     ←/→  prev/next page         ESC   close
     1-7  jump to page            ?     reopen
   =================================================================== */

window.Retro = window.Retro || {};

Retro.Guide = (function () {
  'use strict';

  /* ---------- tiny DOM helpers ---------- */
  const $ = (s, r = document) => r.querySelector(s);
  const h = (tag, attrs = {}, ...kids) => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') el.className = v;
      else if (k === 'dataset') Object.assign(el.dataset, v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null) el.setAttribute(k, v);
    }
    for (const kid of kids) {
      if (kid == null) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  };

  /* =================================================================
     SYNTAX HIGHLIGHTER — small DSL-aware tokenizer (browser-side only)
     ================================================================= */

  const KEYWORDS = new Set([
    'game', 'pieces', 'define', 'color', 'rules', 'controls',
    'snake_mode', 'theme', 'grid', 'block_size', 'background',
    'x', 'lines', 'true', 'false',
  ]);
  const RULE_KEYS = new Set([
    'gravity_speed', 'speedup_every', 'score_per_line', 'bonus_tetris',
    'game_over', 'score_per_food', 'start_length', 'food_count',
    'wrap_edges', 'speed',
  ]);
  const ACTIONS = new Set([
    'move_left', 'move_right', 'move_up', 'move_down',
    'rotate', 'soft_drop', 'hard_drop', 'pause', 'restart', 'quit',
  ]);
  const THEMES = new Set(['NEON', 'CRT_GREEN', 'AMBER', 'MONO', 'DEFAULT']);
  const COLLISION = new Set(['on_top_collision', 'on_self_collision', 'on_wall_collision']);

  function highlight(src) {
    const out = [];
    let i = 0;
    const N = src.length;
    function push(cls, txt) {
      if (cls) out.push(`<span class="syn-${cls}">${escapeHtml(txt)}</span>`);
      else out.push(escapeHtml(txt));
    }
    while (i < N) {
      const c = src[i];
      // line comment
      if (c === '/' && src[i + 1] === '/') {
        let j = i;
        while (j < N && src[j] !== '\n') j++;
        push('comment', src.slice(i, j));
        i = j;
        continue;
      }
      // string
      if (c === '"') {
        let j = i + 1;
        while (j < N && src[j] !== '"' && src[j] !== '\n') j++;
        if (j < N) j++;
        push('string', src.slice(i, j));
        i = j;
        continue;
      }
      // hex color
      if (c === '#') {
        let j = i + 1;
        while (j < N && /[0-9a-fA-F]/.test(src[j])) j++;
        push('hex', src.slice(i, j));
        i = j;
        continue;
      }
      // time literal: digits + 'ms'
      if (/[0-9]/.test(c)) {
        let j = i;
        while (j < N && /[0-9]/.test(src[j])) j++;
        if (src[j] === 'm' && src[j + 1] === 's') {
          push('time', src.slice(i, j + 2));
          i = j + 2;
        } else {
          push('num', src.slice(i, j));
          i = j;
        }
        continue;
      }
      // identifier / keyword
      if (/[A-Za-z_]/.test(c)) {
        let j = i;
        while (j < N && /[A-Za-z0-9_]/.test(src[j])) j++;
        const word = src.slice(i, j);
        let cls = '';
        if (word.startsWith('KEY_'))             cls = 'key';
        else if (KEYWORDS.has(word))             cls = 'kw';
        else if (RULE_KEYS.has(word))            cls = 'rule';
        else if (ACTIONS.has(word))              cls = 'action';
        else if (THEMES.has(word))               cls = 'theme';
        else if (COLLISION.has(word))            cls = 'cond';
        else                                     cls = 'ident';
        push(cls, word);
        i = j;
        continue;
      }
      // punctuation / whitespace
      if (/[\[\],]/.test(c)) {
        push('punct', c);
        i++;
        continue;
      }
      push('', c);
      i++;
    }
    return out.join('');
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[ch]);
  }

  /* =================================================================
     PAGES
     ================================================================= */

  const PAGES = [
    /* --------- 1. WELCOME --------- */
    {
      id: 'welcome',
      title: 'WELCOME',
      render: () => h('div', { class: 'gp gp-welcome' },
        h('pre', { class: 'gp-ascii', 'aria-hidden': 'true' },
`   ____      _             _
  |  _ \\ ___| |_ _ __ ___ | |    __ _ _ __   __ _
  | |_) / _ \\ __| '__/ _ \\| |   / _\` | '_ \\ / _\` |
  |  _ <  __/ |_| | | (_) | |__| (_| | | | | (_| |
  |_| \\_\\___|\\__|_|  \\___/|_____\\__,_|_| |_|\\__, |
                                             |___/`),

        h('h3', { class: 'gp-h' }, '▼ INSERT CARTRIDGE — PLAYER\'S MANUAL ▼'),

        h('p', {},
          'RetroLang is a programming language for retro arcade games. ',
          'You write a ', h('code', {}, '.retro'), ' file describing the game — ',
          'grid, pieces, physics, controls — and a ', h('b', {}, 'six-phase compiler'),
          ' walks the source through Lex → Parse → Semantic → IR → Optimize → Codegen, ',
          'then renders the game live in your browser.'),

        h('div', { class: 'gp-stat-row' },
          h('div', { class: 'gp-stat' }, h('b', {}, '5'),  h('span', {}, 'demo programs')),
          h('div', { class: 'gp-stat' }, h('b', {}, '6'),  h('span', {}, 'compile phases')),
          h('div', { class: 'gp-stat' }, h('b', {}, '2'),  h('span', {}, 'game modes')),
          h('div', { class: 'gp-stat' }, h('b', {}, '5'),  h('span', {}, 'CRT themes')),
        ),

        h('p', { class: 'gp-foot-hint' },
          'Use ', h('kbd', {}, '←'), h('kbd', {}, '→'), ' to navigate · ',
          h('kbd', {}, '1'), '–', h('kbd', {}, '7'), ' jump to page · ',
          h('kbd', {}, 'ESC'), ' close'),
      ),
    },

    /* --------- 2. QUICK START --------- */
    {
      id: 'start',
      title: 'QUICK START',
      render: () => h('div', { class: 'gp gp-steps' },
        h('h3', { class: 'gp-h' }, 'THREE STEPS TO PLAY'),

        h('ol', { class: 'gp-step-list' },
          h('li', {},
            h('span', { class: 'gp-step-num' }, '1'),
            h('div', {},
              h('h4', {}, 'PICK A GAME'),
              h('p', {}, 'The lobby has five demos — Tetris and Snake variants. ',
                         'Click a card, or press number keys ', h('kbd', {}, '1'),
                         '–', h('kbd', {}, '5'), ' to launch instantly.'))),

          h('li', {},
            h('span', { class: 'gp-step-num' }, '2'),
            h('div', {},
              h('h4', {}, 'WATCH IT COMPILE'),
              h('p', {}, 'The CRT screen animates each phase as it runs — ',
                         'token counts, AST nodes, TAC quads, and any ',
                         'optimization rewrites. This is your compiler ',
                         'doing its job in real time.'))),

          h('li', {},
            h('span', { class: 'gp-step-num' }, '3'),
            h('div', {},
              h('h4', {}, 'PLAY'),
              h('p', {}, 'The game launches inside a CRT bezel. The HUD on ',
                         'the right shows score, level/length, and the active ',
                         'control map. Press ', h('kbd', {}, 'R'), ' to restart, ',
                         h('kbd', {}, 'Q'), ' to bail out.'))),
        ),

        h('p', { class: 'gp-tip' }, '▣  Want to write your own program? ',
          'Open the “+ Write your own .retro program” drawer in the lobby ',
          'and paste any source — the compile flow is identical.'),
      ),
    },

    /* --------- 3. THE COMPILER --------- */
    {
      id: 'phases',
      title: 'THE COMPILER',
      render: () => {
        const phases = [
          { n: '①', name: 'LEXER',     out: 'tokens',       why: 'Hand-coded DFA scanner. No re module, no libraries.' },
          { n: '②', name: 'PARSER',    out: 'AST',          why: 'Recursive descent; LL(1) with one peek for piece-shape ambiguity.' },
          { n: '③', name: 'SEMANTIC',  out: 'symbol table', why: 'Type checks, range checks, mode/control compatibility.' },
          { n: '④', name: 'IR',        out: 'GameIR + TAC', why: 'Dual IR: structured object for codegen, flat quads for teaching.' },
          { n: '⑤', name: 'OPTIMIZER', out: 'rewritten IR', why: 'Constant folding, dead-piece elimination, peephole.' },
          { n: '⑥', name: 'CODEGEN',   out: 'runtime',      why: 'On desktop emits pygame; in your browser it’s this Canvas.' },
        ];
        const chain = h('div', { class: 'gp-chain' });
        phases.forEach((p, i) => {
          chain.append(
            h('div', { class: 'gp-chain-node', tabindex: '0' },
              h('div', { class: 'gp-chain-num' }, p.n),
              h('div', { class: 'gp-chain-name' }, p.name),
              h('div', { class: 'gp-chain-out' }, '→ ' + p.out),
              h('div', { class: 'gp-chain-why' }, p.why),
            )
          );
          if (i < phases.length - 1) chain.append(h('div', { class: 'gp-chain-arrow' }, '►'));
        });

        const demoOut = h('pre', { class: 'gp-demo-out trace' },
                           'Click "WATCH IT" to compile the example above through every phase.');
        const demoBtn = h('button', { class: 'primary-btn',
                                      onclick: () => runDemo(demoOut, demoBtn) },
                           '▶ WATCH IT COMPILE');

        return h('div', { class: 'gp gp-phases' },
          h('h3', { class: 'gp-h' }, 'THE 6 COMPILER PHASES'),
          chain,
          h('p', { class: 'gp-sub' },
            'Hover or focus any node above for a one-line summary. ',
            'Below: a small example program compiled live.'),
          h('div', { class: 'gp-demo-row' },
            h('pre', { class: 'gp-demo-src', innerHTML: highlight(SAMPLE_RETRO_SHORT) }),
            h('div', { class: 'gp-demo-arrow' }, '─►'),
            demoOut,
          ),
          h('div', { class: 'gp-demo-cta' }, demoBtn),
        );
      },
    },

    /* --------- 4. WRITE YOUR OWN --------- */
    {
      id: 'lang',
      title: 'WRITE YOUR OWN',
      render: () => {
        const annotated = [
          { line: 'game "MiniDemo"',                    note: 'header — game name (string)' },
          { line: '    grid 6 x 10',                    note: 'playfield in cells, width × height' },
          { line: '    block_size 28',                  note: 'pixel size of each cell' },
          { line: '    background #0D0D1A',             note: 'hex color for empty cells' },
          { line: '    theme NEON',                     note: 'one of NEON, CRT_GREEN, AMBER, MONO, DEFAULT' },
          { line: '',                                   note: '' },
          { line: 'pieces',                             note: 'block — declares Tetris mode' },
          { line: '    define I [1,1,1,1] color #00FFFF', note: 'flat-row shape (1×n)' },
          { line: '    define O [[1,1],[1,1]] color #FFD700', note: 'matrix shape (m×n)' },
          { line: '',                                   note: '' },
          { line: 'rules',                              note: 'physics & scoring' },
          { line: '    gravity_speed 500ms',            note: 'fall every 500 ms' },
          { line: '    score_per_line 100',             note: 'each cleared line = 100 points' },
          { line: '    bonus_tetris 400',               note: 'extra on a 4-line clear' },
          { line: '    game_over on_top_collision',     note: 'condition to end the game' },
          { line: '',                                   note: '' },
          { line: 'controls',                           note: 'action → KEY_* binding' },
          { line: '    move_left  KEY_LEFT',            note: 'tetris-only action' },
          { line: '    hard_drop  KEY_SPACE',           note: '' },
        ];

        const lines = h('div', { class: 'gp-lang-grid' });
        annotated.forEach(({ line, note }, i) => {
          lines.append(
            h('div', { class: 'gp-lang-num' }, line ? String(i + 1).padStart(2, ' ') : ' '),
            h('pre', { class: 'gp-lang-line', innerHTML: line ? highlight(line) : '&nbsp;' }),
            h('div', { class: 'gp-lang-note' }, note ? '◂ ' + note : ''),
          );
        });

        return h('div', { class: 'gp gp-lang' },
          h('h3', { class: 'gp-h' }, 'THE LANGUAGE IN 20 LINES'),
          h('p', { class: 'gp-sub' },
            'Every ', h('code', {}, '.retro'), ' file is line-terminated. ',
            'Blocks (', h('code', {}, 'pieces'), ', ', h('code', {}, 'rules'), ', ',
            h('code', {}, 'controls'), ', ', h('code', {}, 'snake_mode'), ') ',
            'may appear in any order after the ', h('code', {}, 'game'), ' header. ',
            'Comments start with ', h('code', {}, '//'), '.'),

          lines,

          h('p', { class: 'gp-tip' },
            '▣  Want a Snake game instead? Replace the ', h('code', {}, 'pieces'),
            ' block with ', h('code', {}, 'snake_mode'),
            ' (start_length, food_count, wrap_edges, speed) and use ',
            h('code', {}, 'on_self_collision'), ' / ',
            h('code', {}, 'on_wall_collision'), ' as game_over conditions.'),
        );
      },
    },

    /* --------- 5. CONTROLS --------- */
    {
      id: 'keys',
      title: 'CONTROLS',
      render: () => {
        const keyCard = (key, action) =>
          h('div', { class: 'gp-key' },
            h('kbd', { class: 'gp-kbd' }, key),
            h('span', {}, action));

        return h('div', { class: 'gp gp-keys' },
          h('h3', { class: 'gp-h' }, 'KEYBOARD REFERENCE'),

          h('h4', { class: 'gp-h2' }, 'TETRIS'),
          h('div', { class: 'gp-key-grid' },
            keyCard('← →', 'Move horizontally'),
            keyCard('↑',   'Rotate piece'),
            keyCard('↓',   'Soft drop'),
            keyCard('SPACE', 'Hard drop'),
            keyCard('P',   'Pause / resume'),
            keyCard('R',   'Restart'),
            keyCard('Q',   'Quit to lobby'),
          ),

          h('h4', { class: 'gp-h2' }, 'SNAKE'),
          h('div', { class: 'gp-key-grid' },
            keyCard('↑ ↓ ← →', 'Steer (or WASD on Fast Snake)'),
            keyCard('P', 'Pause / resume'),
            keyCard('R', 'Restart'),
            keyCard('Q', 'Quit to lobby'),
          ),

          h('h4', { class: 'gp-h2' }, 'INTERFACE'),
          h('div', { class: 'gp-key-grid' },
            keyCard('1 – 5', 'Quick-launch a lobby demo'),
            keyCard('?',     'Open this manual'),
            keyCard('ESC',   'Close manual / dialog'),
            keyCard('← →',   'Navigate manual pages'),
          ),

          h('p', { class: 'gp-tip' },
            '▣  Bindings are declared per-game in the ', h('code', {}, 'controls'),
            ' block. Snake-only and Tetris-only actions can\'t cross modes — ',
            'the semantic phase will reject mismatches with a line/column error.'),
        );
      },
    },

    /* --------- 6. PRO TIPS --------- */
    {
      id: 'tips',
      title: 'PRO TIPS',
      render: () => h('div', { class: 'gp gp-tips' },
        h('h3', { class: 'gp-h' }, 'NON-OBVIOUS THINGS TO TRY'),
        h('ul', { class: 'gp-tip-list' },
          h('li', {},
            h('b', {}, 'Compile error? Read the caret.'), ' ',
            'The compiler reports phase, line, column and prints the offending line ',
            'with a ', h('code', {}, '^'), ' under the offending token.'),
          h('li', {},
            h('b', {}, 'Watch the optimizer fire.'), ' ',
            'Neon Tetris triggers ', h('code', {}, 'constant-fold'),
            ' on ', h('code', {}, 'bonus_tetris == 4 × score_per_line'),
            ' — the trace will show it.'),
          h('li', {},
            h('b', {}, 'Make a chaotic Tetris.'), ' ',
            'In “+ Write your own .retro program”, set ',
            h('code', {}, 'gravity_speed 100ms'), ' and ',
            h('code', {}, 'speedup_every 1 lines'),
            ' — survive 30 seconds.'),
          h('li', {},
            h('b', {}, 'Themed fast snake.'), ' ',
            'Try ', h('code', {}, 'theme CRT_GREEN'), ', ',
            h('code', {}, 'wrap_edges true'), ', and ',
            h('code', {}, 'speed 60ms'), '.'),
          h('li', {},
            h('b', {}, 'Same source, two surfaces.'), ' ',
            'The very same ', h('code', {}, '.retro'), ' file plays here and on ',
            'the desktop pygame runtime — clone the repo and run ',
            h('code', {}, 'python3 retrolang.py game.retro'), '.'),
          h('li', {},
            h('b', {}, 'Inspect what got compiled.'), ' ',
            'On the play screen, click ', h('b', {}, 'VIEW PHASE TRACE'),
            ' to read the post-optimization TAC quads — the same artefact ',
            'shown by ', h('code', {}, '--debug'), ' on the CLI.'),
        ),
      ),
    },

    /* --------- 7. CREDITS --------- */
    {
      id: 'credits',
      title: 'CREDITS',
      render: () => h('div', { class: 'gp gp-credits' },
        h('h3', { class: 'gp-h' }, 'RETROLANG · CS4031 SPRING 2026'),

        h('div', { class: 'gp-credits-grid' },
          h('div', {},
            h('h4', {}, 'AUTHORS'),
            h('ul', { class: 'gp-credit-list' },
              h('li', {}, 'Syed Taha Zaidi  ', h('span', { class: 'gp-id' }, '23K-0577')),
              h('li', {}, 'Shahmeer Irfan   ', h('span', { class: 'gp-id' }, '23K-0832')),
              h('li', {}, 'Hamza Nasir Lodi ', h('span', { class: 'gp-id' }, '23K-0561')),
            )),

          h('div', {},
            h('h4', {}, 'COURSE'),
            h('p', {}, 'CS4031 — Compiler Construction'),
            h('p', {}, 'Spring 2026'),
            h('p', {}, 'FAST National University of Computer'),
            h('p', {}, 'and Emerging Sciences, Karachi'),
          ),

          h('div', {},
            h('h4', {}, 'SOURCE'),
            h('p', {}, h('a', { href: 'https://github.com/taha-zaidii/RetroLang',
                                target: '_blank', rel: 'noopener' },
              'github.com/taha-zaidii/RetroLang ↗')),
            h('h4', { style: 'margin-top:14px' }, 'LICENSE'),
            h('p', {}, 'Educational use only. Not for commercial distribution. ',
                       'pygame is LGPL.'),
          ),
        ),

        h('p', { class: 'gp-foot-hint' },
          '⏎ END OF MANUAL — Thanks for playing. ',
          h('kbd', {}, 'ESC'), ' to dismiss.'),
      ),
    },
  ];

  // Short snippet for the "WATCH IT" demo on page 3
  const SAMPLE_RETRO_SHORT = `game "Mini"
    grid 4 x 6
    block_size 24
    background #0D0D1A
    theme NEON

pieces
    define I [1,1,1,1] color #00FFFF

rules
    gravity_speed 500ms
    score_per_line 100
    bonus_tetris   400
    game_over      on_top_collision

controls
    move_left  KEY_LEFT
    move_right KEY_RIGHT
    rotate     KEY_UP
    hard_drop  KEY_SPACE
    quit       KEY_Q
`;

  /* =================================================================
     LIVE PHASE DEMO (page 3 "WATCH IT" button)
     ================================================================= */

  let demoRunning = false;
  async function runDemo(out, btn) {
    if (demoRunning) return;
    demoRunning = true;
    btn.disabled = true;
    btn.textContent = '⚙ COMPILING…';
    out.innerHTML = '';

    const append = (cls, text) => {
      const ln = document.createElement('div');
      if (cls) ln.className = cls;
      ln.textContent = text;
      out.appendChild(ln);
      out.scrollTop = out.scrollHeight;
    };
    const wait = ms => new Promise(r => setTimeout(r, ms));

    try {
      append('ph', 'PHASE 1 ▸ Lexical Analysis');
      await wait(220);
      const res = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: SAMPLE_RETRO_SHORT }),
      });
      const j = await res.json();
      if (!j.ok) throw new Error((j.phase || 'compile') + ': ' + (j.message || 'failed'));
      const t = j.trace;

      append('ok', `✓ ${t.tokens} tokens scanned`);
      await wait(200);
      append('ph', 'PHASE 2 ▸ Syntax Analysis');
      await wait(180);
      append('ok', `✓ AST built · ${t.ast_nodes} nodes`);
      await wait(180);
      append('ph', 'PHASE 3 ▸ Semantic Analysis');
      await wait(180);
      append('ok', `✓ symbol table populated · mode=${j.ir.mode}`);
      await wait(180);
      append('ph', 'PHASE 4 ▸ IR Generation');
      await wait(180);
      append('ok', `✓ ${t.tac_before.length} TAC quads emitted`);
      await wait(180);
      append('ph', 'PHASE 5 ▸ Optimization');
      await wait(160);
      if (t.optimization_log.length) {
        for (const line of t.optimization_log) append('dim', '  · ' + line);
      } else {
        append('dim', '  · no rewrites triggered');
      }
      append('ok', `✓ ${t.tac_after.length} TAC quads after opt`);
      await wait(180);
      append('ph', 'PHASE 6 ▸ Code Generation');
      await wait(220);
      append('ok', '✓ runtime ready — would launch in lobby.');
    } catch (e) {
      append('err', '✗ ' + e.message);
    } finally {
      demoRunning = false;
      btn.disabled = false;
      btn.textContent = '▶ RUN AGAIN';
    }
  }

  /* =================================================================
     OVERLAY MOUNT + NAV
     ================================================================= */

  let curIdx = 0;
  let kbBound = null;

  function mount() {
    if ($('#guide')) return;
    const overlay = h('div', { id: 'guide', class: 'guide', hidden: '',
                                role: 'dialog', 'aria-modal': 'true',
                                'aria-labelledby': 'guide-title' });

    const pager = h('div', { class: 'guide-pager', id: 'guide-pager' });
    const title = h('h2', { id: 'guide-title' }, 'PLAYER\'S MANUAL');

    const head = h('header', { class: 'guide-head' },
      h('div', { class: 'guide-title-row' },
        h('span', { class: 'guide-tag' }, 'CARTRIDGE'),
        title),
      pager,
      h('button', { id: 'guide-close', class: 'navbtn',
                    onclick: close, 'aria-label': 'Close manual' }, 'CLOSE ✕'),
    );

    const body = h('main', { class: 'guide-body', id: 'guide-body', tabindex: '-1' });

    const foot = h('footer', { class: 'guide-foot' },
      h('button', { class: 'navbtn', id: 'guide-prev', onclick: prev }, '◀ PREV'),
      h('div', { class: 'guide-hint' },
        h('kbd', {}, '←'), h('kbd', {}, '→'), ' navigate · ',
        h('kbd', {}, '1'), '–', h('kbd', {}, '7'), ' jump · ',
        h('kbd', {}, 'ESC'), ' close'),
      h('button', { class: 'navbtn', id: 'guide-next', onclick: next }, 'NEXT ▶'),
    );

    const frame = h('div', { class: 'guide-frame' }, head, body, foot);
    overlay.append(frame);

    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.body.appendChild(overlay);
  }

  function renderPager() {
    const pager = $('#guide-pager');
    if (!pager) return;
    pager.innerHTML = '';
    PAGES.forEach((p, i) => {
      const dot = h('button', {
        class: 'guide-dot' + (i === curIdx ? ' active' : ''),
        title: `${i + 1}. ${p.title}`,
        'aria-label': `Page ${i + 1}: ${p.title}`,
        onclick: () => goto(i),
      }, h('span', {}, i === curIdx ? p.title : (i + 1)));
      pager.append(dot);
    });
  }

  function renderPage() {
    const body = $('#guide-body');
    if (!body) return;
    body.innerHTML = '';
    body.scrollTop = 0;
    const page = PAGES[curIdx];
    body.appendChild(page.render());
    body.classList.remove('gp-anim');
    void body.offsetWidth; // force reflow so animation re-fires
    body.classList.add('gp-anim');

    const prevBtn = $('#guide-prev');
    const nextBtn = $('#guide-next');
    if (prevBtn) prevBtn.disabled = curIdx === 0;
    if (nextBtn) nextBtn.disabled = curIdx === PAGES.length - 1;

    if (typeof Retro.SFX?.tick === 'function') Retro.SFX.tick();
    body.focus();
    renderPager();
  }

  function goto(idx) {
    curIdx = Math.max(0, Math.min(PAGES.length - 1, idx | 0));
    renderPage();
  }
  function next() { if (curIdx < PAGES.length - 1) goto(curIdx + 1); }
  function prev() { if (curIdx > 0) goto(curIdx - 1); }

  function open(pageIdx = 0) {
    mount();
    const overlay = $('#guide');
    if (!overlay) return;
    overlay.hidden = false;
    overlay.classList.add('open');
    curIdx = pageIdx;
    renderPage();
    Retro.SFX?.beep(880, 0.05);
    if (kbBound) document.removeEventListener('keydown', kbBound);
    kbBound = handleKey;
    document.addEventListener('keydown', kbBound);
    try { localStorage.setItem('retrolang.manualSeen', '1'); } catch {}
    document.documentElement.classList.add('guide-open');
    // Decorate the manual button so the new-visitor hint goes away
    const btn = document.getElementById('manual-btn');
    if (btn) btn.classList.remove('hint');
  }

  function close() {
    const overlay = $('#guide');
    if (!overlay || overlay.hidden) return;
    overlay.classList.remove('open');
    overlay.hidden = true;
    if (kbBound) document.removeEventListener('keydown', kbBound);
    kbBound = null;
    Retro.SFX?.beep(440, 0.04);
    document.documentElement.classList.remove('guide-open');
  }

  function isOpen() {
    const overlay = $('#guide');
    return !!overlay && !overlay.hidden;
  }

  function handleKey(e) {
    if (!isOpen()) return;
    // Don't capture keys if user is typing in an input inside the manual
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;

    if (e.key === 'Escape')           { e.preventDefault(); close(); return; }
    if (e.key === 'ArrowRight' || e.key === 'PageDown')
                                       { e.preventDefault(); next(); return; }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp')
                                       { e.preventDefault(); prev(); return; }
    if (e.key === 'Home')             { e.preventDefault(); goto(0); return; }
    if (e.key === 'End')              { e.preventDefault(); goto(PAGES.length - 1); return; }
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= PAGES.length)  { e.preventDefault(); goto(n - 1); return; }
  }

  function hasBeenSeen() {
    try { return localStorage.getItem('retrolang.manualSeen') === '1'; }
    catch { return false; }
  }

  return { open, close, isOpen, hasBeenSeen, PAGES };
})();

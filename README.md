# RetroLang 🎮

> **A hand-built compiler for a retro arcade scripting language.**  
> Write a `.retro` file. Run the compiler. Watch a fully playable Tetris or Snake window open — every rule, every keybinding, every pixel assembled from your source through six classical compiler phases.

```
   ____      _             _
  |  _ \ ___| |_ _ __ ___ | |    __ _ _ __   __ _
  | |_) / _ \ __| '__/ _ \| |   / _` | '_ \ / _` |
  |  _ <  __/ |_| | | (_) | |__| (_| | | | | (_| |
  |_| \_\___|\__|_|  \___/|_____\__,_|_| |_|\__, |
                                             |___/
```

**CS4031 — Compiler Construction · Spring 2026**  
Syed Taha Zaidi (23K-0577) · Shahmeer Irfan (23K-0832) · Hamza Nasir Lodi (23K-0561)  
FAST National University of Computer and Emerging Sciences, Karachi

---

## Why I Built This

Every semester I watch compiler construction lectures and think "okay, I understand DFAs, I get recursive descent, I can picture IR"— and then the moment I actually have to build one, I realize how far understanding concepts is from implementing them. This project was my attempt to close that gap.

I wanted something that *felt* real — not just a toy that accepts `x = 5 + 3` and calls it a day. The moment I thought "what if the compiler's output was a *running game*?" everything clicked. The language had to be interesting enough to justify a real parser, the semantic phase would have meaningful type rules, the IR would need actual structure, and the code generator would produce something you could actually play.

RetroLang was born from that idea. Write a declarative description of a retro arcade game. Run it through six phases. Play it.

---

## What RetroLang Is

RetroLang is a **declarative domain-specific language** for retro arcade games. A single `.retro` file describes everything:

- The grid dimensions and visual theme
- The pieces (Tetris) or snake configuration
- The physics rules (gravity speed, scoring, speedup)
- The key bindings

The **RetroLang compiler** walks all six classical compiler phases and emits a self-contained Python/pygame module that runs the game.

A single compiler supports two game archetypes:

| Archetype  | Declared with       | What gets generated                             |
|------------|---------------------|-------------------------------------------------|
| **Tetris** | `pieces { ... }`    | falling-piece engine, rotation, line clearing, level-up speed |
| **Snake**  | `snake_mode { ... }`| directional movement, food, growth, wrap-edges  |

---

## Quick Demo

```bash
# 1. Install the only runtime dependency
pip install -r requirements.txt    # pygame >= 2.5.0

# 2. Compile and play Neon Tetris
python3 retrolang.py examples/neontetris.retro

# 3. Compile to Python without launching
python3 retrolang.py examples/snake.retro --emit-python

# 4. See the full compiler trace (tokens → AST → symbol table → IR → opt → codegen)
python3 retrolang.py examples/neontetris.retro --debug

# 5. Or use the interactive launcher (browser UI)
python3 launcher.py
```

> If pygame isn't installed, the compiler still runs — use `--emit-python` or `-o out.py` to capture the generated module without launching it.

---

## The Language

Here is the full source for a 7-piece Neon Tetris game:

```retro
// neontetris.retro — full Tetris with 7 standard pieces and neon theme.
// Demonstrates the falling-piece game mode and progressive difficulty.

game "NeonTetris"
    grid 10 x 20
    block_size 32
    background #0D0D1A
    theme NEON

pieces
    define I [1,1,1,1]                color #00FFFF
    define O [[1,1],[1,1]]             color #FFD700
    define T [[0,1,0],[1,1,1]]         color #FF00FF
    define S [[0,1,1],[1,1,0]]         color #00FF88
    define Z [[1,1,0],[0,1,1]]         color #FF4444
    define L [[1,0],[1,0],[1,1]]       color #FF8800
    define J [[0,1],[0,1],[1,1]]       color #8800FF

rules
    gravity_speed   500ms
    speedup_every   5 lines
    score_per_line  100
    bonus_tetris    400
    game_over       on_top_collision

controls
    move_left  KEY_LEFT
    move_right KEY_RIGHT
    rotate     KEY_UP
    soft_drop  KEY_DOWN
    hard_drop  KEY_SPACE
    pause      KEY_P
    restart    KEY_R
    quit       KEY_Q
```

And a Snake game:

```retro
game "CRT Snake"
    grid 20 x 20
    block_size 24
    background #001100
    theme CRT_GREEN

snake_mode
    start_length 3
    food_count   1
    wrap_edges   false
    speed        150ms

rules
    score_per_food 10
    game_over      on_self_collision

controls
    move_up    KEY_UP
    move_down  KEY_DOWN
    move_left  KEY_LEFT
    move_right KEY_RIGHT
    pause      KEY_P
    restart    KEY_R
    quit       KEY_Q
```

See [`docs/LANGUAGE_MANUAL.md`](docs/LANGUAGE_MANUAL.md) for the complete language specification with all valid tokens, block structures, and constraint ranges.

---

## CLI Reference

```bash
python3 retrolang.py game.retro                  # compile + launch the game
python3 retrolang.py game.retro -o out.py        # emit generated Python to file
python3 retrolang.py game.retro --emit-python    # write .py next to the .retro
python3 retrolang.py game.retro --debug          # full phase trace to stdout
python3 retrolang.py game.retro --no-run         # compile only, don't launch
python3 retrolang.py --interactive               # REPL mode
```

**REPL meta-commands:** `:tokens` · `:ast` · `:symbols` · `:ir` · `:tac` · `:opt` · `:load <file>` · `:game-select` · `:run` · `:help`

**Browser Launcher:**
```bash
python3 launcher.py      # opens http://localhost:7373 — click a game card to compile & play
```

---

## The Compiler Pipeline

This is what I care most about. Six phases, each in its own module, each with a clear input/output contract.

### Phase 1 — Lexical Analysis (`src/lexer.py`)

A hand-coded DFA scanner — no `re` module, no tokenization libraries. The state machine recognizes nine token classes:

| Token     | Pattern                            |
|-----------|------------------------------------|
| `KEYWORD` | `game pieces define color rules controls snake_mode theme grid block_size background x lines true false` |
| `IDENT`   | `[a-zA-Z_][a-zA-Z0-9_]*`          |
| `STRING`  | `"..."` (no multiline)             |
| `HEX`     | `#[0-9a-fA-F]{3,6}`               |
| `TIME`    | `[0-9]+ms`                         |
| `INT`     | `[0-9]+`                           |
| `LBRACK`  | `[`                                |
| `RBRACK`  | `]`                                |
| `COMMA`   | `,`                                |
| `NEWLINE` | `\n` (significant — line-terminated grammar) |

Newline runs are collapsed to a single `NEWLINE`. Comments (`// …`) are silently consumed. Every token carries line and column for downstream error reporting.

The full state diagram (states q0..q12) is in [`docs/DFA.md`](docs/DFA.md).

### Phase 2 — Syntax Analysis (`src/parser.py`)

A recursive-descent parser. The grammar is LL(1) — one token of lookahead suffices everywhere except the `<shape>` production, where we peek at the second token to disambiguate flat-row `[1,1,1,1]` from matrix `[[0,1,0],[1,1,1]]` form.

Key design decisions:
- **Line-terminated statements.** Every block-level statement ends with `NEWLINE`; `_skip_newlines()` absorbs blank lines between statements.
- **Block order independence.** After the `game` header, `pieces`/`snake_mode`/`rules`/`controls` may appear in any order. A dispatch loop handles this cleanly.
- **Duplicate detection** happens here for duplicate block declarations; per-declaration duplicates are caught in Phase 3.

Output is a `Program` AST built from dataclass nodes in `src/ast_nodes.py`. The full grammar in EBNF is in [`docs/GRAMMAR.md`](docs/GRAMMAR.md).

### Phase 3 — Semantic Analysis (`src/semantic.py`)

This phase builds a scoped `SymbolTable` (global scope → block child scopes) and enforces:

- **Type checking** — hex color format, integer ranges, boolean literals, key identifiers, theme names, game-over conditions
- **Uniqueness** — piece names, control actions, rule keys (within their scopes)
- **Cross-block constraints** — `pieces` and `snake_mode` are mutually exclusive; tetris mode requires ≥1 piece; every game must have a `controls` block; control actions must be valid for the declared game mode (e.g., `rotate` is illegal in snake mode)
- **Range checking** — `grid` 1..200, `block_size` 1..128, `gravity_speed` 20..5000 ms, `food_count` 1..20, etc.

Errors surface as `SemanticError` with line, column, and the source line quoted with a caret under the offending token. Worked symbol table walk-through: [`docs/SYMBOL_TABLE.md`](docs/SYMBOL_TABLE.md).

### Phase 4 — IR Generation (`src/ir.py`)

I chose a **dual IR** approach:

- **`GameIR`** — a structured, typed Python object holding every field the code generator needs (grid config, palette, piece list, rules, control map). Think of it as a strongly-typed AST with all semantic sugar stripped out.
- **TAC** (three-address code) — a flat list of quadruples `(op, arg1, arg2, dest)` with ops: `HEADER SET PIECE RULE BIND CONST ADD MUL SUB DIV`.

Both are built in lock-step from the same AST walk. `GameIR` is what the code generator actually consumes; TAC is the classical teaching artifact visible via `--debug`. This avoids the common trap of having to reconstruct structured information from a flat quad list at codegen time.

### Phase 5 — Optimization (`src/optimizer.py`)

Three passes:

| Pass | What it does |
|------|-------------|
| **Constant folding** | Recognizes `bonus_tetris == 4 × score_per_line` and similar patterns; folds any `(ADD\|MUL\|SUB\|DIV) lit lit` TAC quad to `CONST` |
| **Dead-piece elimination** | Removes pieces whose shape contains no `1` cells; in snake mode removes *all* pieces (they are unreachable code) |
| **Peephole** | Collapses consecutive `SET k v / SET k v'` to `SET k v'`; deduplicates identical `BIND` quads |

Every pass appends a human-readable note to `ir.optimization_log`. `--debug` prints a before/after quad diff.

### Phase 6 — Code Generation (`src/codegen.py`)

`generate(ir)` returns a complete, self-contained Python source string. Dispatches on `ir.mode`:

- **Tetris template** — full falling-piece engine: random piece selection, SRS-style rotation, hard drop, line clearing with Tetris bonus, speed escalation (`drop_interval *= 0.85` per level), pause, restart, score display.
- **Snake template** — directional movement, configurable wrap-edges, food respawn, growth, self/wall collision detection driven by `GAME_OVER_CONDS`, score display.

The IR's shapes, colors, rules, and key bindings are embedded as **Python literals** at the top of the generated file — no RetroLang import at runtime. The compiled output is fully standalone and shippable.

---

## Project Structure

```
RetroLang/
├── retrolang.py            # CLI entry point
├── launcher.py             # browser-based demo launcher
├── requirements.txt        # pygame >= 2.5.0
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── lexer.py            # Phase 1 — DFA tokenizer
│   ├── parser.py           # Phase 2 — recursive-descent
│   ├── ast_nodes.py        # AST dataclasses + dump()
│   ├── semantic.py         # Phase 3 — symbol table, type/range checks
│   ├── ir.py               # Phase 4 — GameIR + TAC quadruples
│   ├── optimizer.py        # Phase 5 — fold, dead-piece, peephole
│   ├── codegen.py          # Phase 6 — pygame Python emitter
│   ├── errors.py           # uniform RetroError diagnostic format
│   └── repl.py             # interactive REPL
├── examples/
│   ├── neontetris.retro    # 7-piece Tetris · NEON theme · full controls
│   ├── classictetris.retro # 4-piece Tetris · MONO theme
│   ├── minimal_tetris.retro# smallest valid RetroLang program
│   ├── snake.retro         # CRT-green Snake
│   ├── fastsnake.retro     # AMBER Snake · wrap-around edges
│   └── error_demo.retro    # intentionally broken (semantic errors demo)
├── tests/
│   └── test_compiler.py    # 16 tests: full pipeline + error classes
└── docs/
    ├── LANGUAGE_MANUAL.md  # complete language specification
    ├── ARCHITECTURE.md     # phase-by-phase implementation overview
    ├── GRAMMAR.md          # formal CFG / EBNF
    ├── DFA.md              # lexer state machine + transition table
    ├── PARSE_TREES.md      # two worked parse-tree examples
    ├── SYMBOL_TABLE.md     # filled symbol table walk-through
    └── REFLECTION.md       # challenges, lessons, what I'd do differently
```

---

## Running the Tests

```bash
python3 -m unittest tests.test_compiler -v
```

**16 tests across 4 suites:**

| Suite | Tests |
|-------|-------|
| `TestExamples` | All 5 example `.retro` files compile end-to-end, generate valid Python, and have the correct mode |
| `TestErrorReporting` | Lex/parse/semantic errors fire at the right phase for intentionally-broken inputs |
| `TestOptimization` | Constant-folding fires on neontetris; peephole deduplicates `BIND` quads correctly |
| `TestREPL` | REPL's `_compile_pipeline` function returns correctly typed IR |

All 16 tests pass on Python 3.11+.

---

## Error Reporting

Every phase uses the same diagnostic format:

```
[Semantic error] line 6, col 5: unknown theme 'MATRIX' (valid: AMBER, CRT_GREEN, DEFAULT, MONO, NEON)
    theme MATRIX
    ^
```

The error bubbles up as a typed `RetroError` subclass (`LexError`, `ParseError`, `SemanticError`) and is caught at the CLI entry point, so partial compilation never produces silent garbage.

---

## Compiler-Phase Deliverables (Rubric Mapping)

| Rubric item                       | Where to find it |
|-----------------------------------|-----------------|
| Lexical analyzer (DFA)            | [`docs/DFA.md`](docs/DFA.md) · [`src/lexer.py`](src/lexer.py) |
| Syntax analyzer (CFG/EBNF)        | [`docs/GRAMMAR.md`](docs/GRAMMAR.md) · [`src/parser.py`](src/parser.py) |
| Two parse trees                   | [`docs/PARSE_TREES.md`](docs/PARSE_TREES.md) |
| Semantic analyzer + symbol table  | [`docs/SYMBOL_TABLE.md`](docs/SYMBOL_TABLE.md) · [`src/semantic.py`](src/semantic.py) |
| IR (TAC + GameIR)                 | [`src/ir.py`](src/ir.py) · printed by `--debug` |
| Optimizations (≥ 2)               | [`src/optimizer.py`](src/optimizer.py) — fold + dead-piece + peephole |
| Code generation                   | [`src/codegen.py`](src/codegen.py) — live pygame window |
| Language manual                   | [`docs/LANGUAGE_MANUAL.md`](docs/LANGUAGE_MANUAL.md) |
| Architecture document             | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Test suite (≥ 5 programs)         | [`examples/`](examples/) + [`tests/test_compiler.py`](tests/test_compiler.py) |
| Team reflection                   | [`docs/REFLECTION.md`](docs/REFLECTION.md) |

---

## Design Decisions & What I Learned

**Why a dual IR?** The instinct is to make TAC the only IR and reconstruct structure at codegen. That's painful. Keeping a rich `GameIR` object and a parallel flat TAC was the right call — `GameIR` is easy to emit from, TAC is easy to optimize pattern-match and display.

**Why line-terminated grammar?** Python-style indentation would have been a nightmare to implement correctly. A newline-as-terminator approach — like `retro`'s natural feel — gives a clean LL(1) grammar without needing an indent/dedent lexer.

**Why two game modes in one compiler?** I originally planned only Tetris. Snake came in when I realized the IR was rich enough to dispatch differently at codegen time with almost no extra code. It made Phase 5 more interesting too — the dead-piece optimization actually eliminates unreachable piece definitions in snake mode.

**The hardest part** was the semantic cross-validation: making sure that when you declare `snake_mode`, the controls phase rejects Tetris-only actions like `rotate`. This required the symbol table and the `game_mode` property on the `Program` AST node to be populated before `_check_controls` ran.

---

## Themes Available

| Theme       | Description                        |
|-------------|------------------------------------|
| `NEON`      | Deep navy background, vivid neon piece colors |
| `CRT_GREEN` | Classic green phosphor terminal look |
| `AMBER`     | Warm amber monochrome               |
| `MONO`      | Clean black-and-white minimalist    |
| `DEFAULT`   | Standard Tetris palette             |

---

## License

Educational project for CS4031 — Compiler Construction, FAST-NU, Karachi, Spring 2026.

Not intended for commercial distribution. The pygame runtime dependency is under the LGPL.

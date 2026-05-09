# RetroLang — Language Reference Manual

**Version:** 1.0  **Course:** CS4031 — Compiler Construction (Spring 2026)
**File extension:** `.retro`
**Reference compiler:** `retrolang.py` (Python 3.10+, pygame 2.x for runtime)

---

## 1. Overview

RetroLang is a **declarative domain-specific language** for compiling
playable retro arcade games. A `.retro` file describes the grid, the
pieces, the rules, and the keybindings of a game; the RetroLang
compiler translates it into a self-contained Python/pygame module that
launches and renders the game in real time.

A single compiler supports two game archetypes selected by the presence
of a top-level block:

| Archetype  | Selected by         | Engine                                        |
| ---------- | ------------------- | --------------------------------------------- |
| **Tetris** | `pieces` block      | falling-piece engine, line clearing, scoring  |
| **Snake**  | `snake_mode` block  | directional-movement engine, food and growth  |

A program **must** contain exactly one `game` block, exactly one of
`pieces` / `snake_mode`, and exactly one `controls` block. The `rules`
block is optional but recommended.

---

## 2. Program Structure

```
<game block>
<pieces block>  | <snake_mode block>
<rules block>?
<controls block>
```

Blocks may appear in any order after the `game` header. Whitespace and
indentation are not significant beyond separating tokens; newlines act
as statement terminators. Line comments begin with `//`.

---

## 3. Lexical Structure

| Category    | Form                                                  | Examples              |
| ----------- | ----------------------------------------------------- | --------------------- |
| Keyword     | reserved word                                         | `game`, `pieces`, `define`, `color`, `rules`, `controls`, `snake_mode`, `theme`, `grid`, `block_size`, `background`, `x`, `lines`, `true`, `false` |
| Identifier  | `[A-Za-z_][A-Za-z0-9_]*`                              | `I`, `move_left`, `KEY_LEFT`, `NEON` |
| Integer     | `[0-9]+`                                              | `10`, `400`           |
| Time        | integer immediately followed by `ms`                  | `500ms`, `90ms`       |
| Hex color   | `#` followed by 3 or 6 hex digits (3-form expanded)   | `#0D0D1A`, `#FFD700`  |
| String      | `"..."` (no escapes; no embedded newlines)            | `"NeonTetris"`        |
| Punctuation | `[`, `]`, `,`                                         |                       |
| Newline     | terminates a statement; runs are collapsed            |                       |
| Comment     | `// ...` to end of line, discarded                    |                       |

The full DFA / transition table is given in [DFA.md](DFA.md).

---

## 4. The `game` Block

```
game "<name>"
    grid <int> x <int>
    block_size <int>
    background <hex>
    theme <ident>
```

- `name` — non-empty string used as the window title.
- `grid` — width × height in cells; both must be in `1..200`.
- `block_size` — pixel size of one cell; must be in `1..128`.
- `background` — `#RRGGBB` literal.
- `theme` — one of `NEON`, `CRT_GREEN`, `AMBER`, `MONO`, `DEFAULT`. The
  theme controls HUD text, grid line, and accent colors.

Each property may appear at most once.

---

## 5. The `pieces` Block (Tetris Mode)

```
pieces
    define <name> <shape> color <hex>
    ...
```

- `<name>` — identifier, unique within the block.
- `<shape>` — one of:
  - **flat row**, e.g. `[1,1,1,1]`, automatically lifted to `[[1,1,1,1]]`,
  - **2-D matrix**, e.g. `[[0,1,0],[1,1,1]]` for the T piece.
- All rows of a matrix must have equal length; cells must be `0` or `1`;
  at least one cell must be `1`.

A tetris-mode program must declare at least one piece.

---

## 6. The `snake_mode` Block (Snake Mode)

```
snake_mode
    start_length <int>      // 1..GRID_W*GRID_H, recommended 3..6
    food_count   <int>      // 1..20
    wrap_edges   true|false
    speed        <time>     // 20ms..5000ms
```

`snake_mode` and `pieces` are mutually exclusive: declaring both is a
semantic error.

---

## 7. The `rules` Block

```
rules
    gravity_speed   <time>     // tetris: drop interval, 20..5000 ms
    speedup_every   <int> lines// tetris: lines per level (1..1000)
    score_per_line  <int>      // tetris: points per line cleared
    bonus_tetris    <int>      // tetris: bonus when clearing 4 lines
    score_per_food  <int>      // snake: points per food eaten
    game_over       <ident>    // may appear multiple times
```

Valid `game_over` conditions:
`on_top_collision`, `on_self_collision`, `on_wall_collision`, `on_no_moves`.

Numeric ranges are checked at semantic time — out-of-range values
produce diagnostics with line/column.

---

## 8. The `controls` Block

```
controls
    <action> <key_ident>
    ...
```

Valid keys: `KEY_LEFT`, `KEY_RIGHT`, `KEY_UP`, `KEY_DOWN`, `KEY_SPACE`,
`KEY_RETURN`, `KEY_ESCAPE`, `KEY_P`, `KEY_Q`, `KEY_R`, `KEY_W`, `KEY_A`,
`KEY_S`, `KEY_D`.

Actions are mode-specific:

| Mode    | Allowed actions |
| ------- | ----------------|
| Tetris  | `move_left`, `move_right`, `rotate`, `soft_drop`, `hard_drop`, `pause`, `restart`, `quit` |
| Snake   | `move_up`, `move_down`, `move_left`, `move_right`, `pause`, `restart`, `quit` |

No action and no key may be bound twice.

---

## 9. Type System

RetroLang has six value types: `int`, `time_ms`, `bool`, `hex`,
`identifier`, `string`. Every literal token has a fixed type; the
semantic analyzer rejects type-incorrect uses (e.g. `gravity_speed 500`
without `ms` is a parse error because the parser expects a `TIME` token
after that key).

---

## 10. Memory Model

RetroLang is fully **declarative**: there are no user variables, no
mutation, no expressions, no functions. The "memory" of a compiled
program is the symbol table, which is organized into nested scopes:

```
global
├── pieces          (tetris mode only)
├── snake_mode      (snake mode only)
├── rules
└── controls
```

The runtime memory of the *generated* pygame module is hidden from the
RetroLang programmer — the program simply describes a game; the
generated game loop owns its state.

---

## 11. Error Handling

Errors are reported in a uniform format:

```
[<phase> error] line <L>, col <C>: <message>
    <source line>
    ^
```

Where `<phase>` is `Lexical`, `Syntax`, or `Semantic`. The compiler
fails fast on the first error of a phase. See `examples/error_demo.retro`
for a hand-curated set of common mistakes.

---

## 12. Compiler Invocation

```bash
python retrolang.py game.retro                    # compile + launch
python retrolang.py game.retro -o out.py          # emit Python to file
python retrolang.py game.retro --emit-python      # emit alongside source
python retrolang.py game.retro --debug            # print every phase
python retrolang.py game.retro --no-run           # compile only
python retrolang.py --interactive                 # REPL mode
```

In REPL mode use `:help`, `:tokens`, `:ast`, `:symbols`, `:ir`, `:tac`,
`:opt`, `:load <file>`, `:game-select`, `:run`.

---

## 13. Complete Example

See [examples/neontetris.retro](../examples/neontetris.retro) for the
canonical reference program (NeonTetris with seven standard pieces).

---

End of manual.

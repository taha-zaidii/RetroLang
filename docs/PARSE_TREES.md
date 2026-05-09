# RetroLang Parser — Worked Parse Trees

This document is the **digital reference** for the two handwritten parse
trees required by the project rubric (deliverable A.2). Each tree was
produced by running the actual parser on the given input and walking
the AST it produced; only cosmetic formatting has been added.

---

## Parse Tree #1 — `minimal_tetris.retro`

Input:

```
game "Minimal"
    grid 6 x 10
    block_size 24
    background #000022
    theme DEFAULT

pieces
    define O [[1,1],[1,1]] color #FFFFFF

rules
    gravity_speed  600ms
    score_per_line 50
    game_over      on_top_collision

controls
    move_left  KEY_LEFT
    move_right KEY_RIGHT
    rotate     KEY_UP
    soft_drop  KEY_DOWN
    hard_drop  KEY_SPACE
```

Tree (each node is a non-terminal; leaves are terminals):

```
<program>
├── <game-block>
│   ├── 'game'                                  [KEYWORD]
│   ├── "Minimal"                               [STRING]
│   ├── <game-prop> grid
│   │   ├── 'grid'      'x'
│   │   ├── INT 6      INT 10
│   ├── <game-prop> block_size
│   │   └── INT 24
│   ├── <game-prop> background
│   │   └── HEX #000022
│   └── <game-prop> theme
│       └── IDENT DEFAULT
│
├── <pieces-block>
│   ├── 'pieces'                                [KEYWORD]
│   └── <piece-def>
│       ├── 'define'  IDENT 'O'
│       ├── <shape>   (nested form)
│       │   ├── '[' '[' INT 1 ',' INT 1 ']'
│       │   │   ',' '[' INT 1 ',' INT 1 ']' ']'
│       └── 'color'  HEX '#FFFFFF'
│
├── <rules-block>
│   ├── 'rules'                                 [KEYWORD]
│   ├── <rule-stmt> gravity_speed → TIME 600
│   ├── <rule-stmt> score_per_line → INT 50
│   └── <rule-stmt> game_over → IDENT on_top_collision
│
└── <controls-block>
    ├── 'controls'                              [KEYWORD]
    ├── <control-binding> IDENT move_left  IDENT KEY_LEFT
    ├── <control-binding> IDENT move_right IDENT KEY_RIGHT
    ├── <control-binding> IDENT rotate     IDENT KEY_UP
    ├── <control-binding> IDENT soft_drop  IDENT KEY_DOWN
    └── <control-binding> IDENT hard_drop  IDENT KEY_SPACE
```

Key derivations to highlight in the handwritten version:

- `<program> ⇒ <game-block> <pieces-block> <rules-block> <controls-block>`
- `<shape> ⇒ '[' <int-row> ',' <int-row> ']'` (the **2-D matrix** form
  of `<shape>`, taken because the second token after the opening `[` is
  another `[`).

---

## Parse Tree #2 — `snake.retro`

Input (abridged):

```
game "RetroSnake"
    grid 20 x 20
    block_size 24
    background #001100
    theme CRT_GREEN

snake_mode
    start_length 3
    food_count   1
    wrap_edges   false
    speed        200ms

rules
    score_per_food 50
    game_over      on_self_collision
    game_over      on_wall_collision

controls
    move_up    KEY_UP
    move_down  KEY_DOWN
    move_left  KEY_LEFT
    move_right KEY_RIGHT
    pause      KEY_P
    restart    KEY_R
    quit       KEY_Q
```

Tree:

```
<program>
├── <game-block>
│   ├── 'game' STRING "RetroSnake"
│   ├── <game-prop> grid     → INT 20  'x'  INT 20
│   ├── <game-prop> block_size → INT 24
│   ├── <game-prop> background → HEX #001100
│   └── <game-prop> theme    → IDENT CRT_GREEN
│
├── <snake-mode-block>
│   ├── 'snake_mode'
│   ├── <snake-prop> start_length → INT 3
│   ├── <snake-prop> food_count   → INT 1
│   ├── <snake-prop> wrap_edges   → KEYWORD false
│   └── <snake-prop> speed        → TIME 200
│
├── <rules-block>
│   ├── 'rules'
│   ├── <rule-stmt> score_per_food → INT 50
│   ├── <rule-stmt> game_over      → IDENT on_self_collision
│   └── <rule-stmt> game_over      → IDENT on_wall_collision   (legitimate repeat)
│
└── <controls-block>
    ├── 'controls'
    ├── <control-binding>  move_up    KEY_UP
    ├── <control-binding>  move_down  KEY_DOWN
    ├── <control-binding>  move_left  KEY_LEFT
    ├── <control-binding>  move_right KEY_RIGHT
    ├── <control-binding>  pause      KEY_P
    ├── <control-binding>  restart    KEY_R
    └── <control-binding>  quit       KEY_Q
```

Things to highlight when transcribing this tree by hand:

- `<program>` here selects the **Snake archetype** because the second
  block is `<snake-mode-block>` rather than `<pieces-block>`. The
  semantic phase (Phase 3) records this choice as `program.game_mode =
  "snake"`, which the code generator dispatches on in Phase 6.
- `game_over` legitimately appears **twice** under `<rules-block>`. The
  semantic analyzer accumulates these into a single
  `game_over_conditions = [...]` list rather than reporting a duplicate
  rule.

---

## How to verify these trees yourself

```bash
python3 retrolang.py examples/minimal_tetris.retro --debug --no-run
python3 retrolang.py examples/snake.retro          --debug --no-run
```

The `Phase 2: Syntax Analysis (AST)` section of the debug output prints
the same tree structure shown above (with concrete line/col annotations).

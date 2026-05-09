# RetroLang Semantic Analyzer — Symbol Table Walk-Through

Digital reference for the handwritten symbol table required by the
project rubric (deliverable A.3). Every cell below was produced by
running `python3 retrolang.py examples/neontetris.retro --debug --no-run`
and reading the output of Phase 3.

---

## Scope structure

```
┌─────────────────────────────────────────────────────────────┐
│ global scope                                                │
│   game_name, grid_w, grid_h, block_size, background, theme  │
│                                                             │
│   ┌─────────────┐ ┌──────────────┐ ┌─────────┐ ┌──────────┐ │
│   │  pieces     │ │  snake_mode  │ │  rules  │ │ controls │ │
│   │  (tetris)   │ │  (snake)     │ │         │ │          │ │
│   │  I,O,T,S,Z, │ │  start_length│ │ gravity │ │ move_*   │ │
│   │  L,J        │ │  food_count  │ │ ...     │ │ rotate   │ │
│   │             │ │  wrap_edges  │ │         │ │ ...      │ │
│   │             │ │  speed       │ │         │ │          │ │
│   └─────────────┘ └──────────────┘ └─────────┘ └──────────┘ │
│        (only one of pieces / snake_mode is populated)       │
└─────────────────────────────────────────────────────────────┘
```

Each inner scope has the global scope as its parent, so a name lookup
walks inward → outward and reports the most local definition.

---

## Filled symbol table — `neontetris.retro`

| Scope        | Name           | Kind     | Type        | Value                    | Defined |
| ------------ | -------------- | -------- | ----------- | ------------------------ | ------- |
| global       | game_name      | config   | string      | "NeonTetris"             | line 4  |
| global       | grid_w         | config   | int         | 10                       | line 4  |
| global       | grid_h         | config   | int         | 20                       | line 4  |
| global       | block_size     | config   | int         | 32                       | line 4  |
| global       | background     | config   | hex         | #0D0D1A                  | line 4  |
| global       | theme          | config   | identifier  | NEON                     | line 4  |
| pieces       | I              | piece    | shape       | { shape, color #00FFFF } | line 11 |
| pieces       | O              | piece    | shape       | { shape, color #FFD700 } | line 12 |
| pieces       | T              | piece    | shape       | { shape, color #FF00FF } | line 13 |
| pieces       | S              | piece    | shape       | { shape, color #00FF88 } | line 14 |
| pieces       | Z              | piece    | shape       | { shape, color #FF4444 } | line 15 |
| pieces       | L              | piece    | shape       | { shape, color #FF8800 } | line 16 |
| pieces       | J              | piece    | shape       | { shape, color #8800FF } | line 17 |
| rules        | gravity_speed  | rule     | time_ms     | 500                      | line 20 |
| rules        | speedup_every  | rule     | int         | 5                        | line 21 |
| rules        | score_per_line | rule     | int         | 100                      | line 22 |
| rules        | bonus_tetris   | rule     | int         | 400                      | line 23 |
| rules        | game_over      | rule     | identifier  | on_top_collision         | line 24 |
| controls     | move_left      | control  | identifier  | KEY_LEFT                 | line 27 |
| controls     | move_right     | control  | identifier  | KEY_RIGHT                | line 28 |
| controls     | rotate         | control  | identifier  | KEY_UP                   | line 29 |
| controls     | soft_drop      | control  | identifier  | KEY_DOWN                 | line 30 |
| controls     | hard_drop      | control  | identifier  | KEY_SPACE                | line 31 |
| controls     | pause          | control  | identifier  | KEY_P                    | line 32 |
| controls     | restart        | control  | identifier  | KEY_R                    | line 33 |
| controls     | quit           | control  | identifier  | KEY_Q                    | line 34 |

---

## Filled symbol table — `snake.retro`

The snake-mode program lights up the `snake_mode` scope instead:

| Scope      | Name          | Kind       | Type        | Value           | Defined |
| ---------- | ------------- | ---------- | ----------- | --------------- | ------- |
| global     | game_name     | config     | string      | "RetroSnake"    | line 4  |
| global     | grid_w        | config     | int         | 20              | line 4  |
| global     | grid_h        | config     | int         | 20              | line 4  |
| global     | block_size    | config     | int         | 24              | line 4  |
| global     | background    | config     | hex         | #001100         | line 4  |
| global     | theme         | config     | identifier  | CRT_GREEN       | line 4  |
| snake_mode | start_length  | snake_prop | int         | 3               | line 10 |
| snake_mode | food_count    | snake_prop | int         | 1               | line 10 |
| snake_mode | wrap_edges    | snake_prop | bool        | false           | line 10 |
| snake_mode | speed         | snake_prop | time_ms     | 200             | line 10 |
| rules      | score_per_food| rule       | int         | 50              | line 16 |
| rules      | game_over     | rule       | identifier  | [on_self_collision, on_wall_collision] | line 17 |
| controls   | move_up       | control    | identifier  | KEY_UP          | line 22 |
| controls   | move_down     | control    | identifier  | KEY_DOWN        | line 23 |
| controls   | move_left     | control    | identifier  | KEY_LEFT        | line 24 |
| controls   | move_right    | control    | identifier  | KEY_RIGHT       | line 25 |
| controls   | pause         | control    | identifier  | KEY_P           | line 26 |
| controls   | restart       | control    | identifier  | KEY_R           | line 27 |
| controls   | quit          | control    | identifier  | KEY_Q           | line 28 |

Notes for the handwritten version:

- The `game_over` row in `snake.retro` shows the **list-collapsing**
  behavior: two repeated `game_over` lines collapse into a single
  symbol whose value is a list. The semantic analyzer
  ([src/semantic.py](../src/semantic.py)) does this in `_check_rules`.
- `pieces` and `snake_mode` are mutually exclusive scopes: only the one
  applicable to the program's mode is populated. The other is empty.

---

## Errors detected by the symbol table

When transcribing the handwritten artifact, also include a short table
of *rejected* programs to demonstrate type/scope checks. Run:

```bash
python3 retrolang.py examples/error_demo.retro
```

to see semantic errors triggered by:

| Error class                       | Trigger                                |
| --------------------------------- | -------------------------------------- |
| Duplicate piece in `pieces` scope | two `define I` lines                   |
| Unknown `game_over` value         | `game_over on_typo_collision`          |
| Duplicate action in `controls`    | two `move_left` bindings               |
| Out-of-range integer              | `gravity_speed 7000ms`                 |
| Non-hex character in color        | `background #ZZZZZZ`                   |
| Mode/action mismatch              | `move_up` action under tetris mode     |

Each error is reported with the standard
`[Semantic error] line L, col C: ...` format, including the offending
source line and a caret pointing at the column.

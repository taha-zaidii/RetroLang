# RetroLang Compiler — Architecture Document

This document gives a phase-by-phase walk-through of the RetroLang
implementation. Every phase is contained in a single source file under
[src/](../src/) and is exercised end-to-end by [retrolang.py](../retrolang.py).

---

## High-level pipeline

```
   ┌──────────┐   ┌──────────┐   ┌────────────┐   ┌──────┐   ┌─────────┐   ┌─────────────┐
   │  source  │──▶│  Lexer   │──▶│  Parser    │──▶│ Sem. │──▶│   IR    │──▶│  Optimizer  │──▶ codegen
   │  .retro  │   │  Phase 1 │   │  Phase 2   │   │ Ph.3 │   │  Ph.4   │   │   Phase 5   │       Phase 6
   └──────────┘   └──────────┘   └────────────┘   └──────┘   └─────────┘   └─────────────┘
                       │              │              │           │              │              │
                  Tokens[]         AST(Program)   SymbolTable  GameIR + TAC   GameIR'+TAC'    Python module
```

All phases use a uniform error type (`RetroError` subclasses) carrying
phase, line, and column. A failure in any phase is caught by
`retrolang.py main()` and printed in the standard caret format.

---

## File map

| Path                         | Phase           | Role                                        |
| ---------------------------- | --------------- | ------------------------------------------- |
| `src/errors.py`              | shared          | `RetroError`, `LexError`, `ParseError`, `SemanticError` |
| `src/lexer.py`               | Phase 1         | DFA tokenizer producing `Token[]`           |
| `src/ast_nodes.py`           | shared          | dataclass AST nodes + `dump()` pretty-printer |
| `src/parser.py`              | Phase 2         | recursive-descent → `Program` AST           |
| `src/semantic.py`            | Phase 3         | scoped `SymbolTable`, type & range checks   |
| `src/ir.py`                  | Phase 4         | `GameIR` object graph + TAC quadruples      |
| `src/optimizer.py`           | Phase 5         | constant-fold, dead-piece, peephole         |
| `src/codegen.py`             | Phase 6         | emits `pygame` Python source                |
| `src/repl.py`                | front-end       | interactive REPL (`--interactive`)          |
| `retrolang.py`               | front-end       | CLI driver, `--debug` phase trace           |

---

## Phase 1 — Lexical analysis

`Lexer.tokenize()` walks the source character-by-character, never
backtracks more than one position, and emits `Token(type, value, line, col)`
records. The token classes are the ones documented in
[GRAMMAR.md](GRAMMAR.md). Whitespace and `// …` comments are consumed
silently. Newlines are emitted as `NEWLINE` tokens (and runs are
collapsed) because the grammar is line-terminated.

The DFA is hand-coded: each state is a different code path inside
`tokenize()`, and the transitions match the table in [DFA.md](DFA.md)
exactly. We deliberately do **not** use a regex engine for the DFA —
regex is used only as a *spec* of token classes.

Errors: a single illegal character produces `LexError` with the line
quoted and a caret under the offending column.

---

## Phase 2 — Syntax analysis

`Parser.parse()` is a textbook recursive-descent parser. The grammar is
LL(1) with one-token lookahead, so each non-terminal is a method, and
each method dispatches on `self._peek().type` (and sometimes on its
lexeme for keywords).

Notable design choices:

- **Line-terminated grammar.** Every block-level statement ends with a
  `NEWLINE` token; the parser calls `_skip_newlines()` between
  statements so blank lines are tolerated.
- **`<shape>` ambiguity resolution.** Both forms of `<shape>` start with
  `[`. We resolve with a single token of lookahead: if the second token
  is another `[`, we are in matrix form; otherwise flat-row form.
- **Block dispatch in any order.** After the `<game-block>`, the
  remaining four block kinds may appear in any order. We loop and
  dispatch on the leading keyword.

---

## Phase 3 — Semantic analysis

`SemanticAnalyzer.analyze()` builds a `SymbolTable` with a `global`
scope and child scopes for each present block (`pieces` xor `snake_mode`,
plus `rules`, `controls`). For each declaration we:

1. Insert a `Symbol(name, kind, type_, value, scope, line, col)` into
   the appropriate scope.
2. Enforce uniqueness (piece names, control actions, rule keys).
3. Range-check numeric values (`grid` 1..200, `block_size` 1..128,
   `gravity_speed` 20..5000 ms, etc.).
4. Validate enum-like identifiers (theme names, key names, game-over
   conditions, mode-specific actions).
5. Cross-validate: `pieces` and `snake_mode` are mutually exclusive;
   tetris-mode programs must declare ≥1 piece; every game must have a
   `controls` block.

Errors are surfaced as `SemanticError` with line/col.

---

## Phase 4 — Intermediate representation

The lowering produces **two** complementary IRs:

- **`GameIR`** (the main IR) — a typed, structured object holding every
  field needed by the code generator: grid config, palette, piece list,
  rule values, control map. This is what Phase 5 rewrites and Phase 6
  consumes.
- **TAC** (three-address-code) — a flat list of quadruples
  `(op, arg1, arg2, dest)`. Quadruple ops include `HEADER`, `SET`,
  `PIECE`, `RULE`, `BIND`, plus `CONST`/`ADD`/`MUL`/`SUB`/`DIV` for
  arithmetic that the optimizer can fold. The TAC is preserved primarily
  as a course-deliverable artifact (visible via `--debug`); Phase 6
  itself reads `GameIR`.

This dual representation matches the "structured + flat" split common in
real compilers (e.g. LLVM IR + MIR) and makes the optimizer's job easy.

---

## Phase 5 — Optimization

Three optimizations operate on the IR pair:

| Pass                       | Effect on IR                                    | Effect on TAC          |
| -------------------------- | ----------------------------------------------- | ---------------------- |
| **constant folding**       | recognises `bonus_tetris == 4 × score_per_line` patterns; folds any `(ADD/MUL/SUB/DIV) lit lit` quad to `CONST` | rewrites quads in place |
| **dead-piece elimination** | removes pieces with no `1` cells; in snake mode removes **all** pieces (unreachable) | drops their `PIECE` quads |
| **peephole**               | n/a (TAC-level)                                 | collapses consecutive `SET k v / SET k v'` → `SET k v'` and deduplicates identical `BIND` quads |

Every pass appends a human-readable line to `ir.optimization_log` so
the grader can see which optimizations fired. `--debug` prints the
before/after TAC counts and a diff of removed quads.

---

## Phase 6 — Code generation

`codegen.generate(ir)` returns a complete Python source string. The
generator dispatches on `ir.mode`:

- **Tetris template** — falling-piece engine with rotation, line
  clearing, level-up speed escalation (`drop_interval *= 0.85` per
  level), and Tetris bonus.
- **Snake template** — directional engine with `WRAP_EDGES`,
  food-respawn, growth, and self/wall collision detection driven by
  `GAME_OVER_CONDS`.

Both templates embed the IR's piece shapes, colors, rules, and key
bindings as **Python literals** at the top of the file, so the
generated module is self-contained — it does not import any RetroLang
code at runtime. This is what makes `--emit-python` shippable.

The CLI then either:
- writes the generated source via `-o` / `--emit-python`, or
- writes it to a temp file and `exec_module`-s it (default behavior),
launching the pygame window.

---

## Cross-cutting concerns

### Error reporting

A single uniform format across phases:

```
[<Phase> error] line <L>, col <C>: <message>
    <source line>
    ^
```

Each phase converts its raw exceptions into `RetroError` subclasses
that carry the phase tag.

### Debug visibility

`--debug` prints:

1. token stream
2. AST dump
3. symbol table (all scopes flattened)
4. unoptimized GameIR + TAC
5. optimization log + diff
6. optimized GameIR + TAC
7. line count of generated Python

This makes every internal artifact required by the rubric visible at the
command line.

### REPL

`--interactive` exposes the same artifacts as meta-commands
(`:tokens`, `:ast`, `:symbols`, `:ir`, `:tac`, `:opt`) plus
`:game-select` for the Choose-Your-Own-Adventure loader.

---

## Why two IRs?

A common course-project trap is to make TAC the *only* IR — which
forces the code generator to reconstitute a structured view from a flat
quad list. We avoided that by treating the structured `GameIR` as the
real IR (good for codegen) and the TAC as a teaching artifact (good for
showing classical compiler concepts in `--debug`). Both stay in sync
because Phase 4 builds them in lock-step.

# RetroLang — Team Reflection

**Course:** CS4031 — Compiler Construction (Spring 2026)
**Project:** RetroLang — Retro Arcade Game Scripting Language

---

## Challenges Faced and Solutions

**1. Disambiguating piece-shape syntax.**
Our `<shape>` non-terminal accepts both a flat row (`[1,1,1,1]`) and a
2-D matrix (`[[1,1],[1,1]]`). Both forms begin with `[`, which initially
caused an LL(1) FIRST/FIRST conflict. We resolved it with **one-token
lookahead**: after consuming the opening `[`, the parser inspects the
next token — if it is another `[`, the matrix production is taken;
otherwise the flat row production. This kept the grammar LL(1) and
avoided introducing a non-trivial backtracking parser.

**2. Multi-mode game engine with one compiler.**
Supporting both Tetris and Snake from one source language meant the
semantic analyzer had to enforce different rules per mode (allowed
actions, required blocks, valid game-over conditions). We solved this
by exposing a single `program.game_mode` property derived at parse time
(presence of `snake_mode` ⇒ "snake", else "tetris") and dispatching on
it in both `_check_controls` and the code generator. The runtime
templates remain entirely separate, but the front-end is unified.

**3. Designing a useful TAC for a declarative language.**
RetroLang has no expressions, no functions, and no control flow —
classical TAC ops like `ADD t1 t2 t3` rarely appear. We were tempted to
skip TAC entirely, but the rubric required it. Our solution was to use
TAC as a **teaching IR** alongside a structured `GameIR`: every AST
construct lowers to both, so `--debug` can show classical quads
(`HEADER`, `SET`, `PIECE`, `RULE`, `BIND`) while the code generator
consumes the easier-to-traverse `GameIR`. This dual representation also
gave the optimizer a clean place to do constant folding (on TAC) and
dead-piece elimination (on `GameIR`), which is the same split real
compilers make between low-level and high-level passes.

**4. Generating runnable pygame code, not just a bytecode dump.**
The proposal called for a "live playable game" as Phase 6 output. We
chose to emit a fully self-contained Python file that embeds every IR
literal at the top. This means `--emit-python` produces a portable
artifact a user can run without RetroLang installed, and our compiler's
runtime path simply `exec_module`s the same string. Keeping the
templates literal-driven (no string-substitution helpers, no f-strings
inside f-strings) made the code generator easy to debug and easy to
extend with new themes or rules.

---

## What We Learned About Compiler Design

- **Front ends are line-by-line; back ends are pattern-by-pattern.**
  The lexer/parser/semantic phases were almost mechanical once we wrote
  down the grammar and validation rules. Code generation, by contrast,
  required us to *think backwards* from "what does the runtime need" to
  "what does the IR have to carry," which reshaped the IR design twice
  before we settled on `GameIR`.
- **A symbol table is a deliverable, not a side-effect.** We initially
  used a plain dict for symbol lookup. Once we added the per-block
  scopes required by the rubric, dict lookups stopped being enough and
  the `Scope` class with parent-chain lookup paid for itself
  immediately — both for error messages ("first defined at line X") and
  for the `--debug` symbol-table dump.
- **An optimization pass needs evidence.** Constant folding on a
  declarative language sounds trivial because the inputs already are
  constants. The interesting evidence is the *recognition* of patterns
  (e.g. `bonus_tetris == 4 × score_per_line`) and the **before/after
  diff** the rubric asks for. Logging every pass's effect into
  `ir.optimization_log` made these passes graspable rather than
  invisible.
- **`--debug` is the best test you have.** Because every phase prints a
  human-readable artifact, regressions in any one phase show up
  immediately. We caught two parser bugs and a semantic bug just by
  diffing `--debug` output between commits.

---

## Future Improvements

- **Generalize pieces to N rotation states.** Today we rotate matrices
  at runtime in the generated game loop. Pre-computing all four
  rotations during code generation would let us enforce shape symmetry
  rules at compile time and would speed up the generated game loop on
  weak hardware.
- **A second back end.** The code generator currently emits Python.
  Adding an alternative back end that emits Chip-8 assembly (or even
  WebAssembly via a small VM) would make RetroLang a true cross-target
  compiler and would push our IR design further.
- **Sound and animation primitives.** The proposal mentioned chiptune
  music. A future `sounds` block could emit pygame mixer calls; an
  `animations` block could let pieces animate their lock-in.
- **Persistent high scores via a `data` block.** Today every game
  starts at 0. A small statically-allocated key/value store, declared
  in a new top-level block, would give the generated runtime a save
  file with no user code.
- **A small unit-test DSL for `.retro` files.** Today our test suite
  asserts that programs compile and that the generated Python parses.
  A `# expect tokens: ...` directive in `.retro` files would let us
  assert exact lexer/parser output, turning the example folder into a
  golden test corpus.

---

## Individual Contributions

| Member               | ID        | Primary contributions                                                              |
| -------------------- | --------- | ---------------------------------------------------------------------------------- |
| Syed Taha Zaidi      | 23K-0577  | Language design & EBNF grammar; lexer (Phase 1) and parser (Phase 2); CLI driver and REPL meta-commands; final integration & end-to-end testing. |
| Shahmeer Irfan       | 23K-0832  | Semantic analyzer (Phase 3) and symbol-table design; intermediate representation (Phase 4) — both `GameIR` and TAC; error-reporting framework (`RetroError` and the caret format) shared across phases. |
| Hamza Nasir Lodi     | 23K-0561  | Optimizer (Phase 5) — constant folding, dead-piece elimination, peephole; code generator (Phase 6) — both Tetris and Snake pygame templates; example `.retro` programs; documentation pack (manual, architecture, DFA, parse trees, symbol table, this reflection). |

All three members met for two integration sessions where the
phase-by-phase deliverables were merged, and we reviewed each other's
phases in pairs (Phase 1↔3, 2↔4, 5↔6) before final submission.

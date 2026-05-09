# RetroLang Grammar (CFG / EBNF)

Non-terminals are written `<like-this>`. Terminals are written in
**bold** (here as `**lit**`) or as token names (`INT`, `STRING`, etc.).
Optional items use `[...]`, repetition uses `{...}`, alternation uses
`|`. The grammar is **LL(1)** once `NEWLINE` is treated as a statement
terminator by the lexer.

---

## Top-level

```ebnf
<program>          ::= <game-block> { <body-block> }

<body-block>       ::= <pieces-block>
                     | <snake-mode-block>
                     | <rules-block>
                     | <controls-block>
```

A program contains exactly one `<game-block>` and, in any order, the
remaining blocks. The semantic phase enforces:

- exactly one of `<pieces-block>` / `<snake-mode-block>`, and
- exactly one `<controls-block>`.

---

## Game header

```ebnf
<game-block>       ::= **game** STRING NEWLINE { <game-prop> }

<game-prop>        ::= **grid** INT **x** INT NEWLINE
                     | **block_size** INT NEWLINE
                     | **background** HEX NEWLINE
                     | **theme** IDENT NEWLINE
```

The four `<game-prop>` alternatives are pairwise disjoint on their
leading keyword, so the parser is LL(1). Duplicate properties are
caught semantically.

---

## Pieces block

```ebnf
<pieces-block>     ::= **pieces** NEWLINE { <piece-def> }

<piece-def>        ::= **define** IDENT <shape> **color** HEX NEWLINE

<shape>            ::= **[** <shape-tail>
<shape-tail>       ::= INT { **,** INT } **]**            // flat row form
                     | <int-row> { **,** <int-row> } **]**// 2-D matrix form
<int-row>          ::= **[** INT { **,** INT } **]**
```

The `<shape>` non-terminal uses **one-token lookahead** to disambiguate
flat from nested: after consuming the opening `[`, the next token is
either `INT` (flat) or another `[` (nested). This avoids the FIRST/FIRST
conflict that would otherwise arise.

---

## Snake mode block

```ebnf
<snake-mode-block> ::= **snake_mode** NEWLINE { <snake-prop> }

<snake-prop>       ::= **start_length** INT NEWLINE
                     | **food_count**   INT NEWLINE
                     | **wrap_edges**   ( **true** | **false** ) NEWLINE
                     | **speed**        TIME NEWLINE
```

(`start_length`, `food_count`, `wrap_edges`, `speed` are matched as
IDENT tokens by the lexer; the parser checks the lexeme value.)

---

## Rules block

```ebnf
<rules-block>      ::= **rules** NEWLINE { <rule-stmt> }

<rule-stmt>        ::= **gravity_speed**   TIME             NEWLINE
                     | **speedup_every**   INT **lines**    NEWLINE
                     | **score_per_line**  INT              NEWLINE
                     | **score_per_food**  INT              NEWLINE
                     | **bonus_tetris**    INT              NEWLINE
                     | **game_over**       IDENT            NEWLINE
```

`game_over` is the only rule that may appear more than once in a single
block (e.g. snake games typically declare both
`on_self_collision` and `on_wall_collision`).

---

## Controls block

```ebnf
<controls-block>   ::= **controls** NEWLINE { <control-binding> }

<control-binding>  ::= IDENT IDENT NEWLINE                  // action key
```

The first `IDENT` is the action name; the second is a `KEY_*`
identifier. Both validity sets are checked semantically.

---

## Lexical rules (regex form)

```regex
KEYWORD  : game | pieces | define | color | rules | controls
         | snake_mode | theme | grid | block_size | background
         | x | lines | true | false
IDENT    : [A-Za-z_][A-Za-z0-9_]*
INT      : [0-9]+
TIME     : [0-9]+ ms
HEX      : # ([0-9A-Fa-f]{6} | [0-9A-Fa-f]{3})
STRING   : " [^"\n]* "
LBRACK   : \[
RBRACK   : \]
COMMA    : ,
NEWLINE  : \r? \n
COMMENT  : // [^\n]*       (skipped)
WS       : [ \t]+          (skipped)
```

Every keyword is also a valid identifier shape; the lexer first
recognizes an IDENT and **then** promotes it to KEYWORD if its lexeme is
in the reserved set. This is the standard "scan-and-classify" approach.

---

## Left recursion / common prefixes

The grammar contains no left recursion (`<program>` and every
`<*-block>` start with a literal keyword token). The only place a common
prefix could arise is in `<shape>`, where both alternatives begin with
`[`; we resolve this with a single token of lookahead, as documented
above.

---

## Parse trees

Two complete parse trees for sample inputs are given in
[PARSE_TREES.md](PARSE_TREES.md).

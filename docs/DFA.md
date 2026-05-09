# RetroLang Lexical Analyzer — DFA / Transition Table

This document is the **digital reference** for the hand-drawn DFA the
team will scan and submit per the project rubric (deliverable A.1). The
state machine below is implemented one-for-one in [src/lexer.py](../src/lexer.py).

---

## Alphabet

```
Σ = { letter, digit, hex_digit, _, ", #, [, ], ',', /, m, s, x,
      space, tab, newline, ms_pair (= the literal pair 'ms') }
```

(`hex_digit` overlaps `letter` and `digit`; the lexer disambiguates by
the entry state.)

---

## States

| State | Role                                                  |
| ----- | ----------------------------------------------------- |
| q0    | start / between tokens                                |
| q1    | inside an identifier or keyword                       |
| q2    | inside an integer literal                             |
| q3    | post-integer, decide INT vs TIME (saw `m`)            |
| q4    | post-integer, saw `ms`, emit TIME                     |
| q5    | inside a string literal `"..."`                       |
| q6    | string accept (saw closing `"`)                       |
| q7    | hex literal — after `#`, consuming hex digits         |
| q8    | comment — after first `/`, expecting second `/`       |
| q9    | comment body — discarded until newline                |
| qF    | accepting/final (token emitted, return to q0)         |

---

## Transition table

```
            letter    digit    _       "       #       [       ]       ,       /       newline   space/tab   ms (lookahead)
q0          q1        q2       q1      q5      q7      qF[L]   qF[R]   qF[,]   q8      qF[NL]    q0          —
q1          q1        q1       q1      —       —       —       —       —       —       —         qF[ID/KW]   —
q2          —         q2       —       —       —       —       —       —       —       —         qF[INT]     q3
q3          (s)→q4    error    error   —       —       —       —       —       —       —         —           —
q4          —         —        —       —       —       —       —       —       —       —         qF[TIME]    —
q5          q5        q5       q5      q6      q5      q5      q5      q5      q5      error     q5          —
q6          —         —        —       —       —       —       —       —       —       —         qF[STR]     —
q7          q7(hex)   q7       —       —       —       —       —       —       —       —         qF[HEX]     —
q8          —         —        —       —       —       —       —       —       q9      —         —           —
q9          q9        q9       q9      q9      q9      q9      q9      q9      q9      q0(skip)  q9          —
```

Notes:
- `qF[X]` means: emit a token of class `X` and reset to q0 (the input
  character that triggered the transition is **not** consumed when the
  transition is on whitespace/newline; for bracket/comma it **is**).
- The `ms` lookahead from q2 means: after digits, peek the next two
  characters. If they are `m`,`s` and the character after is **not** an
  identifier continuation, take the q2→q3→q4 path and emit TIME;
  otherwise emit INT and stay in q0.
- After q1 finishes, the lexeme is looked up in the keyword set and
  promoted from IDENT to KEYWORD if present (this is a *post-processing*
  step, not part of the DFA proper, in the standard scanner discipline).

---

## Token classes recognized

| Token   | Regex (used as spec, **not** as runtime regex) |
| ------- | ---------------------------------------------- |
| KEYWORD | reserved set; recognized via IDENT post-classification |
| IDENT   | `[A-Za-z_][A-Za-z0-9_]*`                       |
| INT     | `[0-9]+`                                       |
| TIME    | `[0-9]+ ms`                                    |
| HEX     | `#[0-9A-Fa-f]{3}` \| `#[0-9A-Fa-f]{6}`         |
| STRING  | `"[^"\n]*"`                                    |
| LBRACK  | `\[`                                           |
| RBRACK  | `\]`                                           |
| COMMA   | `,`                                            |
| NEWLINE | `\r?\n` (collapses runs)                       |

Whitespace and `// ... \n` comments are lexer-internal and never produce
tokens.

---

## DFA diagram (ASCII layout for the handwritten transcription)

```
                     letter/_                  digit
                ┌────────────┐            ┌────────────┐
                │            │            │            │
                ▼            │            ▼            │
   ┌──┐       ┌────┐         │          ┌────┐         │
   │q0│──────▶│ q1 │─────────┘          │ q2 │─────────┘
   └──┘       └────┘  (delim) ──▶ qF    └────┘  (delim) ──▶ qF
     │                                    │
     │ "                                  │ 'm'(s)
     ▼                                    ▼
   ┌────┐  not "      ┌────┐            ┌────┐  's'    ┌────┐ delim
   │ q5 │──────────▶  │ q5 │            │ q3 │ ──────▶ │ q4 │──▶ qF (TIME)
   └────┘             └────┘            └────┘         └────┘
     │ "
     ▼
   ┌────┐  delim
   │ q6 │──▶ qF (STRING)
   └────┘

   q0 ─#─▶ q7 ──hex──▶ q7 ──delim──▶ qF (HEX)
   q0 ─/─▶ q8 ─/─▶ q9 ─newline─▶ q0      (comment skip)
   q0 ─[─▶ qF (LBRACK)        q0 ─]─▶ qF (RBRACK)
   q0 ─,─▶ qF (COMMA)         q0 ─\n─▶ qF (NEWLINE)
   q0 ─ws─▶ q0
```

The team should redraw this as the scanned hand-drawing required by the
rubric; the structure above is exactly what `Lexer.tokenize()` walks.

---

## Worked example

Input fragment: `gravity_speed 500ms`

```
char    state-before   action                           state-after
'g'     q0             start ident                       q1
'r'     q1             continue ident                    q1
...
'd'     q1             continue ident                    q1
' '     q1             emit IDENT "gravity_speed"        q0
'5'     q0             start integer                     q2
'0'     q2             continue integer                  q2
'0'     q2             continue integer                  q2
'm'     q2             saw m, peek next                  q3
's'     q3             confirmed ms, peek delim          q4
' '     q4             emit TIME 500                     q0
```

Result: `IDENT 'gravity_speed'` then `TIME 500`.

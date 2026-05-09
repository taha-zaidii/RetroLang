"""
RetroLang lexical analyzer (Phase 1).

Hand-coded DFA-style scanner. Each state is a code path in `next_token`;
we never use a regex engine for the DFA itself (regexes are only used as
a *spec* for token classes in docs/DFA.md). Tokens carry line and column
so later phases can report errors at the right spot.

Token categories:
  KEYWORD       game pieces define color rules controls snake_mode theme
                grid block_size background x lines true false
  IDENT         user names, action names, KEY_*, theme names, game-over conditions
  STRING        "..."
  HEX           #RRGGBB or #RGB
  TIME          digits followed by 'ms'   (e.g. 500ms)
  INT           decimal integer
  LBRACK RBRACK COMMA NEWLINE EOF COMMENT(skipped)

The DFA itself (states q0..q12) is documented in docs/DFA.md.
"""

from dataclasses import dataclass
from typing import List
from .errors import LexError, SourceContext


# Reserved words (keywords) — recognized after the IDENT DFA state
# matches an identifier; we then look up the lexeme here. This keeps the
# DFA small while still allowing many keywords.
KEYWORDS = {
    "game", "pieces", "define", "color",
    "rules", "controls", "snake_mode", "theme",
    "grid", "block_size", "background",
    "x", "lines", "true", "false",
}


@dataclass
class Token:
    type: str
    value: object
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.col})"


class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.ctx = SourceContext(source)
        self.pos = 0
        self.line = 1
        self.col = 1

    # ---------- DFA primitives ----------

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _err(self, msg, line, col):
        raise LexError(msg, line, col, self.ctx.line_at(line))

    # ---------- main tokenization ----------

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < len(self.src):
            ch = self._peek()

            # Skip horizontal whitespace
            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            # NEWLINE — significant as a statement terminator
            if ch == "\n":
                line, col = self.line, self.col
                self._advance()
                # collapse runs of blank lines into one NEWLINE
                if not tokens or tokens[-1].type != "NEWLINE":
                    tokens.append(Token("NEWLINE", "\\n", line, col))
                continue

            # Comments: // ... end-of-line
            if ch == "/" and self._peek(1) == "/":
                while self.pos < len(self.src) and self._peek() != "\n":
                    self._advance()
                continue

            line, col = self.line, self.col

            # Punctuation
            if ch == "[":
                self._advance(); tokens.append(Token("LBRACK", "[", line, col)); continue
            if ch == "]":
                self._advance(); tokens.append(Token("RBRACK", "]", line, col)); continue
            if ch == ",":
                self._advance(); tokens.append(Token("COMMA", ",", line, col)); continue

            # String literal
            if ch == '"':
                tokens.append(self._scan_string(line, col)); continue

            # Hex color literal
            if ch == "#":
                tokens.append(self._scan_hex(line, col)); continue

            # Number — may become INT or TIME (e.g., 500ms)
            if ch.isdigit():
                tokens.append(self._scan_number(line, col)); continue

            # Identifier / keyword
            if ch.isalpha() or ch == "_":
                tokens.append(self._scan_ident(line, col)); continue

            self._err(f"unexpected character {ch!r}", line, col)

        tokens.append(Token("EOF", None, self.line, self.col))
        return tokens

    # ---------- DFA states ----------

    def _scan_string(self, line, col) -> Token:
        self._advance()  # opening "
        start = self.pos
        while self.pos < len(self.src) and self._peek() != '"':
            if self._peek() == "\n":
                self._err("unterminated string literal", line, col)
            self._advance()
        if self.pos >= len(self.src):
            self._err("unterminated string literal", line, col)
        value = self.src[start:self.pos]
        self._advance()  # closing "
        return Token("STRING", value, line, col)

    def _scan_hex(self, line, col) -> Token:
        self._advance()  # consume '#'
        start = self.pos
        while self.pos < len(self.src) and self._peek() in "0123456789abcdefABCDEF":
            self._advance()
        digits = self.src[start:self.pos]
        if len(digits) not in (3, 6):
            self._err(f"hex color must have 3 or 6 hex digits, got {len(digits)}", line, col)
        # normalize 3-digit to 6-digit
        if len(digits) == 3:
            digits = "".join(c + c for c in digits)
        return Token("HEX", "#" + digits.upper(), line, col)

    def _scan_number(self, line, col) -> Token:
        start = self.pos
        while self.pos < len(self.src) and self._peek().isdigit():
            self._advance()
        # Time literal: number immediately followed by 'ms'
        if self._peek() == "m" and self._peek(1) == "s" and not (
            self.pos + 2 < len(self.src) and (self.src[self.pos + 2].isalnum() or self.src[self.pos + 2] == "_")
        ):
            num = int(self.src[start:self.pos])
            self._advance(); self._advance()  # consume 'm', 's'
            return Token("TIME", num, line, col)
        return Token("INT", int(self.src[start:self.pos]), line, col)

    def _scan_ident(self, line, col) -> Token:
        start = self.pos
        while self.pos < len(self.src) and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self.src[start:self.pos]
        if lexeme in KEYWORDS:
            return Token("KEYWORD", lexeme, line, col)
        return Token("IDENT", lexeme, line, col)


def tokenize(source: str) -> List[Token]:
    return Lexer(source).tokenize()


def format_tokens(tokens: List[Token]) -> str:
    """Used by --debug to print the token stream."""
    out = []
    for t in tokens:
        if t.type == "NEWLINE":
            out.append(f"  {t.line:3}:{t.col:<3}  NEWLINE")
        else:
            out.append(f"  {t.line:3}:{t.col:<3}  {t.type:<8} {t.value!r}")
    return "\n".join(out)

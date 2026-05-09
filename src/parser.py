"""
RetroLang syntax analyzer (Phase 2).

Recursive-descent parser. The grammar is given in EBNF in docs/GRAMMAR.md
and is LL(1) once the lexer treats NEWLINE as a statement terminator.

Top-level grammar:
  <program>      ::= <game_block> ( <pieces_block> | <snake_mode_block>
                                  | <rules_block>  | <controls_block> )+
  <game_block>   ::= "game" STRING NEWLINE <game_prop>+
  <game_prop>    ::= "grid" INT "x" INT NEWLINE
                   | "block_size" INT NEWLINE
                   | "background" HEX NEWLINE
                   | "theme" IDENT NEWLINE
"""

from typing import List, Optional
from .lexer import Token
from .ast_nodes import (
    Program, GameHeader, PiecesBlock, PieceDef,
    SnakeModeBlock, RulesBlock, RuleStmt,
    ControlsBlock, ControlBinding,
)
from .errors import ParseError, SourceContext


class Parser:
    def __init__(self, tokens: List[Token], source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self.ctx = SourceContext(source)

    # ---------- token helpers ----------

    def _peek(self, offset: int = 0) -> Token:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return t

    def _check(self, type_: str, value=None) -> bool:
        t = self._peek()
        if t.type != type_:
            return False
        return value is None or t.value == value

    def _match(self, type_: str, value=None) -> Optional[Token]:
        if self._check(type_, value):
            return self._advance()
        return None

    def _expect(self, type_: str, value=None) -> Token:
        t = self._peek()
        if not self._check(type_, value):
            want = f"{type_}" + (f" {value!r}" if value is not None else "")
            raise ParseError(
                f"expected {want}, got {t.type} {t.value!r}",
                t.line, t.col, self.ctx.line_at(t.line),
            )
        return self._advance()

    def _skip_newlines(self):
        while self._match("NEWLINE"):
            pass

    # ---------- grammar productions ----------

    def parse(self) -> Program:
        self._skip_newlines()
        prog = Program(line=1, col=1)
        prog.header = self._parse_game_block()

        while not self._check("EOF"):
            self._skip_newlines()
            if self._check("EOF"):
                break
            t = self._peek()
            if t.type != "KEYWORD":
                raise ParseError(
                    f"expected block keyword (pieces, snake_mode, rules, controls), got {t.value!r}",
                    t.line, t.col, self.ctx.line_at(t.line),
                )
            if t.value == "pieces":
                if prog.pieces is not None:
                    raise ParseError("duplicate 'pieces' block", t.line, t.col, self.ctx.line_at(t.line))
                prog.pieces = self._parse_pieces_block()
            elif t.value == "snake_mode":
                if prog.snake_mode is not None:
                    raise ParseError("duplicate 'snake_mode' block", t.line, t.col, self.ctx.line_at(t.line))
                prog.snake_mode = self._parse_snake_mode_block()
            elif t.value == "rules":
                if prog.rules is not None:
                    raise ParseError("duplicate 'rules' block", t.line, t.col, self.ctx.line_at(t.line))
                prog.rules = self._parse_rules_block()
            elif t.value == "controls":
                if prog.controls is not None:
                    raise ParseError("duplicate 'controls' block", t.line, t.col, self.ctx.line_at(t.line))
                prog.controls = self._parse_controls_block()
            else:
                raise ParseError(
                    f"unexpected keyword {t.value!r} at top level",
                    t.line, t.col, self.ctx.line_at(t.line),
                )

        return prog

    # ----- game block -----

    def _parse_game_block(self) -> GameHeader:
        kw = self._expect("KEYWORD", "game")
        name_tok = self._expect("STRING")
        self._expect("NEWLINE")
        header = GameHeader(line=kw.line, col=kw.col, name=name_tok.value)
        # consume one or more game_prop lines
        seen = set()
        while self._check("KEYWORD") and self._peek().value in (
            "grid", "block_size", "background", "theme"
        ):
            prop_tok = self._advance()
            prop = prop_tok.value
            if prop in seen:
                raise ParseError(
                    f"duplicate property {prop!r} in game block",
                    prop_tok.line, prop_tok.col, self.ctx.line_at(prop_tok.line),
                )
            seen.add(prop)
            if prop == "grid":
                w = self._expect("INT").value
                self._expect("KEYWORD", "x")
                h = self._expect("INT").value
                header.grid_w = w
                header.grid_h = h
            elif prop == "block_size":
                header.block_size = self._expect("INT").value
            elif prop == "background":
                header.background = self._expect("HEX").value
            elif prop == "theme":
                header.theme = self._expect("IDENT").value
            self._expect("NEWLINE")
            self._skip_newlines()
        return header

    # ----- pieces block -----

    def _parse_pieces_block(self) -> PiecesBlock:
        kw = self._expect("KEYWORD", "pieces")
        self._expect("NEWLINE")
        block = PiecesBlock(line=kw.line, col=kw.col)
        self._skip_newlines()
        while self._check("KEYWORD", "define"):
            block.pieces.append(self._parse_piece_def())
            self._skip_newlines()
        return block

    def _parse_piece_def(self) -> PieceDef:
        kw = self._expect("KEYWORD", "define")
        name = self._expect("IDENT").value
        shape = self._parse_shape()
        self._expect("KEYWORD", "color")
        color = self._expect("HEX").value
        self._expect("NEWLINE")
        return PieceDef(line=kw.line, col=kw.col, name=name, shape=shape, color=color)

    def _parse_shape(self) -> List[List[int]]:
        """
        Shape can be:
          [1,1,1,1]            — flat row, normalized to [[1,1,1,1]]
          [[1,1],[1,1]]        — 2D matrix
        """
        self._expect("LBRACK")
        first = self._peek()
        # Look ahead — does the first element start with another LBRACK?
        if first.type == "LBRACK":
            rows = [self._parse_int_row()]
            while self._match("COMMA"):
                rows.append(self._parse_int_row())
            self._expect("RBRACK")
            return rows
        # flat row
        elements = [self._expect("INT").value]
        while self._match("COMMA"):
            elements.append(self._expect("INT").value)
        self._expect("RBRACK")
        return [elements]

    def _parse_int_row(self) -> List[int]:
        self._expect("LBRACK")
        elements = [self._expect("INT").value]
        while self._match("COMMA"):
            elements.append(self._expect("INT").value)
        self._expect("RBRACK")
        return elements

    # ----- snake_mode block -----

    def _parse_snake_mode_block(self) -> SnakeModeBlock:
        kw = self._expect("KEYWORD", "snake_mode")
        self._expect("NEWLINE")
        block = SnakeModeBlock(line=kw.line, col=kw.col)
        self._skip_newlines()
        valid = {"start_length", "food_count", "wrap_edges", "speed"}
        seen = set()
        while self._check("IDENT") and self._peek().value in valid:
            name_tok = self._advance()
            prop = name_tok.value
            if prop in seen:
                raise ParseError(
                    f"duplicate snake_mode property {prop!r}",
                    name_tok.line, name_tok.col, self.ctx.line_at(name_tok.line),
                )
            seen.add(prop)
            if prop == "start_length":
                block.start_length = self._expect("INT").value
            elif prop == "food_count":
                block.food_count = self._expect("INT").value
            elif prop == "wrap_edges":
                # accept 'true'/'false' KEYWORDs
                t = self._peek()
                if t.type == "KEYWORD" and t.value in ("true", "false"):
                    self._advance()
                    block.wrap_edges = (t.value == "true")
                else:
                    raise ParseError(
                        f"expected true/false, got {t.value!r}",
                        t.line, t.col, self.ctx.line_at(t.line),
                    )
            elif prop == "speed":
                block.speed_ms = self._expect("TIME").value
            self._expect("NEWLINE")
            self._skip_newlines()
        return block

    # ----- rules block -----

    def _parse_rules_block(self) -> RulesBlock:
        kw = self._expect("KEYWORD", "rules")
        self._expect("NEWLINE")
        block = RulesBlock(line=kw.line, col=kw.col)
        self._skip_newlines()
        # rule statements use IDENT keys (since they're domain words, not reserved)
        while self._check("IDENT"):
            block.rules.append(self._parse_rule_stmt())
            self._skip_newlines()
        return block

    def _parse_rule_stmt(self) -> RuleStmt:
        key_tok = self._expect("IDENT")
        key = key_tok.value
        # Decide expected value form by key
        if key in ("score_per_line", "score_per_food", "bonus_tetris"):
            value = self._expect("INT").value
        elif key in ("gravity_speed",):
            value = self._expect("TIME").value
        elif key == "speedup_every":
            n = self._expect("INT").value
            self._expect("KEYWORD", "lines")
            value = n  # implicit unit: lines
        elif key == "game_over":
            value = self._expect("IDENT").value
        else:
            # Generic fallback: accept INT, TIME, or IDENT.
            t = self._peek()
            if t.type in ("INT", "TIME", "IDENT"):
                value = self._advance().value
            else:
                raise ParseError(
                    f"unexpected value for rule {key!r}",
                    t.line, t.col, self.ctx.line_at(t.line),
                )
        self._expect("NEWLINE")
        return RuleStmt(line=key_tok.line, col=key_tok.col, key=key, value=value)

    # ----- controls block -----

    def _parse_controls_block(self) -> ControlsBlock:
        kw = self._expect("KEYWORD", "controls")
        self._expect("NEWLINE")
        block = ControlsBlock(line=kw.line, col=kw.col)
        self._skip_newlines()
        while self._check("IDENT"):
            action_tok = self._advance()
            key_tok = self._expect("IDENT")
            block.bindings.append(ControlBinding(
                line=action_tok.line, col=action_tok.col,
                action=action_tok.value, key=key_tok.value,
            ))
            self._expect("NEWLINE")
            self._skip_newlines()
        return block


def parse(tokens: List[Token], source: str = "") -> Program:
    return Parser(tokens, source).parse()

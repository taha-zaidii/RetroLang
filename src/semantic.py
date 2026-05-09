"""
RetroLang semantic analyzer (Phase 3).

Responsibilities:
  - Build a scoped symbol table (global game scope -> per-block scopes).
  - Type-check every value: hex-color format, integer ranges, key idents,
    boolean values, game-over conditions, theme identifiers.
  - Detect duplicates (piece names, control bindings, rule keys).
  - Cross-validate: at least one piece in tetris mode; snake_mode forbids
    pieces; controls reference actions appropriate for the game mode.

Output: a populated SymbolTable hung off the Program node, ready for IR.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .ast_nodes import (
    Program, GameHeader, PiecesBlock, PieceDef,
    SnakeModeBlock, RulesBlock, RuleStmt,
    ControlsBlock, ControlBinding,
)
from .errors import SemanticError, SourceContext


VALID_KEYS = {
    "KEY_LEFT", "KEY_RIGHT", "KEY_UP", "KEY_DOWN",
    "KEY_SPACE", "KEY_RETURN", "KEY_ESCAPE",
    "KEY_P", "KEY_Q", "KEY_R", "KEY_W", "KEY_A", "KEY_S", "KEY_D",
}

VALID_THEMES = {"NEON", "CRT_GREEN", "AMBER", "MONO", "DEFAULT"}

VALID_GAME_OVER = {
    "on_top_collision",
    "on_self_collision",
    "on_wall_collision",
    "on_no_moves",
}

TETRIS_ACTIONS = {
    "move_left", "move_right", "rotate", "soft_drop",
    "hard_drop", "pause", "restart", "quit",
}

SNAKE_ACTIONS = {
    "move_up", "move_down", "move_left", "move_right",
    "pause", "restart", "quit",
}


@dataclass
class Symbol:
    name: str
    kind: str         # 'piece' | 'rule' | 'control' | 'config' | 'snake_prop'
    type_: str        # 'hex' | 'int' | 'time_ms' | 'bool' | 'identifier' | 'shape' | 'string'
    value: Any
    scope: str
    line: int
    col: int


@dataclass
class Scope:
    name: str
    parent: Optional["Scope"] = None
    symbols: Dict[str, Symbol] = field(default_factory=dict)

    def define(self, sym: Symbol):
        self.symbols[sym.name] = sym

    def has(self, name: str) -> bool:
        if name in self.symbols:
            return True
        return self.parent.has(name) if self.parent else False

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        return self.parent.lookup(name) if self.parent else None


@dataclass
class SymbolTable:
    """The compile-time symbol table: a stack of scopes plus a flat list
    of every symbol definition (used by --debug to dump scope info)."""
    global_scope: Scope = field(default_factory=lambda: Scope("global"))
    all_scopes: List[Scope] = field(default_factory=list)
    flat: List[Symbol] = field(default_factory=list)

    def __post_init__(self):
        self.all_scopes.append(self.global_scope)

    def push_scope(self, name: str, parent: Scope) -> Scope:
        s = Scope(name, parent)
        self.all_scopes.append(s)
        return s

    def add(self, sym: Symbol):
        self.flat.append(sym)


class SemanticAnalyzer:
    def __init__(self, program: Program, source: str = ""):
        self.prog = program
        self.ctx = SourceContext(source)
        self.table = SymbolTable()
        self.errors: List[SemanticError] = []

    # ---------- error helpers ----------

    def _err(self, msg, line, col):
        raise SemanticError(msg, line, col, self.ctx.line_at(line))

    # ---------- entry point ----------

    def analyze(self) -> SymbolTable:
        if self.prog.header is None:
            self._err("missing 'game' header block", 1, 1)
        self._check_header(self.prog.header)

        if self.prog.snake_mode is not None and self.prog.pieces is not None:
            self._err(
                "snake_mode and pieces blocks are mutually exclusive",
                self.prog.snake_mode.line, self.prog.snake_mode.col,
            )

        if self.prog.snake_mode is None and (self.prog.pieces is None or len(self.prog.pieces.pieces) == 0):
            self._err(
                "tetris-mode programs must declare at least one piece",
                self.prog.header.line, self.prog.header.col,
            )

        if self.prog.pieces:
            self._check_pieces(self.prog.pieces)
        if self.prog.snake_mode:
            self._check_snake(self.prog.snake_mode)
        if self.prog.rules:
            self._check_rules(self.prog.rules)
        if self.prog.controls:
            self._check_controls(self.prog.controls)
        else:
            self._err(
                "missing 'controls' block — every game must define key bindings",
                self.prog.header.line, self.prog.header.col,
            )

        return self.table

    # ---------- per-block validation ----------

    def _check_header(self, h: GameHeader):
        scope = self.table.global_scope
        if not h.name or len(h.name) == 0:
            self._err("game name must be a non-empty string", h.line, h.col)
        if h.grid_w <= 0 or h.grid_h <= 0:
            self._err(
                f"grid dimensions must be positive (got {h.grid_w}x{h.grid_h})",
                h.line, h.col,
            )
        if h.grid_w > 200 or h.grid_h > 200:
            self._err(
                f"grid too large (max 200x200, got {h.grid_w}x{h.grid_h})",
                h.line, h.col,
            )
        if h.block_size <= 0 or h.block_size > 128:
            self._err(
                f"block_size must be in 1..128 (got {h.block_size})",
                h.line, h.col,
            )
        self._check_hex(h.background, "background", h.line, h.col)
        if h.theme not in VALID_THEMES:
            self._err(
                f"unknown theme {h.theme!r} (valid: {', '.join(sorted(VALID_THEMES))})",
                h.line, h.col,
            )
        # Record symbols
        for k, v, t in [
            ("game_name", h.name, "string"),
            ("grid_w", h.grid_w, "int"),
            ("grid_h", h.grid_h, "int"),
            ("block_size", h.block_size, "int"),
            ("background", h.background, "hex"),
            ("theme", h.theme, "identifier"),
        ]:
            sym = Symbol(k, "config", t, v, "global", h.line, h.col)
            scope.define(sym); self.table.add(sym)

    def _check_hex(self, color: str, what: str, line, col):
        if not (isinstance(color, str) and color.startswith("#") and len(color) == 7):
            self._err(f"{what} hex color must be of form #RRGGBB (got {color!r})", line, col)
        for c in color[1:]:
            if c not in "0123456789ABCDEF":
                self._err(f"{what} contains non-hex digit {c!r}", line, col)

    def _check_pieces(self, pieces: PiecesBlock):
        scope = self.table.push_scope("pieces", self.table.global_scope)
        seen = {}
        for p in pieces.pieces:
            if p.name in seen:
                self._err(
                    f"duplicate piece name {p.name!r} (first defined at line {seen[p.name]})",
                    p.line, p.col,
                )
            seen[p.name] = p.line
            self._check_shape(p)
            self._check_hex(p.color, f"piece {p.name!r} color", p.line, p.col)
            sym = Symbol(p.name, "piece", "shape", {"shape": p.shape, "color": p.color},
                         "pieces", p.line, p.col)
            scope.define(sym); self.table.add(sym)

    def _check_shape(self, p: PieceDef):
        if not p.shape or not isinstance(p.shape, list):
            self._err(f"piece {p.name!r} has empty shape", p.line, p.col)
        row_lens = {len(r) for r in p.shape}
        if len(row_lens) != 1:
            self._err(
                f"piece {p.name!r} rows must all have the same length",
                p.line, p.col,
            )
        for row in p.shape:
            for cell in row:
                if cell not in (0, 1):
                    self._err(
                        f"piece {p.name!r} cells must be 0 or 1 (got {cell})",
                        p.line, p.col,
                    )
        # must contain at least one filled cell
        if not any(c == 1 for row in p.shape for c in row):
            self._err(f"piece {p.name!r} contains no filled cells", p.line, p.col)

    def _check_snake(self, s: SnakeModeBlock):
        scope = self.table.push_scope("snake_mode", self.table.global_scope)
        if s.start_length < 1:
            self._err(f"start_length must be >= 1 (got {s.start_length})", s.line, s.col)
        if s.food_count < 1 or s.food_count > 20:
            self._err(f"food_count must be in 1..20 (got {s.food_count})", s.line, s.col)
        if s.speed_ms < 20 or s.speed_ms > 5000:
            self._err(
                f"speed must be in 20ms..5000ms (got {s.speed_ms}ms)",
                s.line, s.col,
            )
        for k, v, t in [
            ("start_length", s.start_length, "int"),
            ("food_count", s.food_count, "int"),
            ("wrap_edges", s.wrap_edges, "bool"),
            ("speed", s.speed_ms, "time_ms"),
        ]:
            sym = Symbol(k, "snake_prop", t, v, "snake_mode", s.line, s.col)
            scope.define(sym); self.table.add(sym)

    def _check_rules(self, rules: RulesBlock):
        scope = self.table.push_scope("rules", self.table.global_scope)
        # game_over may legitimately appear multiple times; everything else
        # is unique within the block.
        seen = {}
        for r in rules.rules:
            if r.key != "game_over" and r.key in seen:
                self._err(
                    f"duplicate rule {r.key!r} (first at line {seen[r.key]})",
                    r.line, r.col,
                )
            seen[r.key] = r.line
            self._validate_rule(r)
            sym = Symbol(r.key, "rule", self._rule_type(r.key), r.value,
                         "rules", r.line, r.col)
            # for repeated game_over, store list under same name
            existing = scope.symbols.get(r.key)
            if existing and r.key == "game_over":
                if not isinstance(existing.value, list):
                    existing.value = [existing.value]
                existing.value.append(r.value)
            else:
                scope.define(sym); self.table.add(sym)

    def _rule_type(self, key: str) -> str:
        return {
            "gravity_speed": "time_ms",
            "speedup_every": "int",
            "score_per_line": "int",
            "score_per_food": "int",
            "bonus_tetris": "int",
            "game_over": "identifier",
        }.get(key, "identifier")

    def _validate_rule(self, r: RuleStmt):
        k, v = r.key, r.value
        if k == "gravity_speed":
            if not isinstance(v, int) or v < 20 or v > 5000:
                self._err(f"gravity_speed must be 20ms..5000ms (got {v})", r.line, r.col)
        elif k == "speedup_every":
            if not isinstance(v, int) or v < 1 or v > 1000:
                self._err(f"speedup_every must be 1..1000 lines (got {v})", r.line, r.col)
        elif k in ("score_per_line", "score_per_food", "bonus_tetris"):
            if not isinstance(v, int) or v < 0 or v > 1_000_000:
                self._err(f"{k} must be 0..1000000 (got {v})", r.line, r.col)
        elif k == "game_over":
            if v not in VALID_GAME_OVER:
                self._err(
                    f"unknown game_over condition {v!r} "
                    f"(valid: {', '.join(sorted(VALID_GAME_OVER))})",
                    r.line, r.col,
                )
        else:
            self._err(f"unknown rule {k!r}", r.line, r.col)

    def _check_controls(self, ctrl: ControlsBlock):
        scope = self.table.push_scope("controls", self.table.global_scope)
        valid_actions = SNAKE_ACTIONS if self.prog.game_mode == "snake" else TETRIS_ACTIONS
        seen_actions = {}
        seen_keys = {}
        for b in ctrl.bindings:
            if b.action not in valid_actions:
                self._err(
                    f"action {b.action!r} not valid in {self.prog.game_mode} mode "
                    f"(valid: {', '.join(sorted(valid_actions))})",
                    b.line, b.col,
                )
            if b.key not in VALID_KEYS:
                self._err(
                    f"unknown key {b.key!r} (valid: {', '.join(sorted(VALID_KEYS))})",
                    b.line, b.col,
                )
            if b.action in seen_actions:
                self._err(
                    f"duplicate binding for action {b.action!r} (first at line {seen_actions[b.action]})",
                    b.line, b.col,
                )
            if b.key in seen_keys:
                self._err(
                    f"key {b.key!r} bound twice (first at line {seen_keys[b.key]} as {seen_keys[b.key]!r})",
                    b.line, b.col,
                )
            seen_actions[b.action] = b.line
            seen_keys[b.key] = b.line
            sym = Symbol(b.action, "control", "identifier", b.key,
                         "controls", b.line, b.col)
            scope.define(sym); self.table.add(sym)


def analyze(program: Program, source: str = "") -> SymbolTable:
    return SemanticAnalyzer(program, source).analyze()


def format_symbol_table(table: SymbolTable) -> str:
    out = []
    out.append("Scope               | Name              | Kind        | Type        | Value")
    out.append("-" * 90)
    for scope in table.all_scopes:
        for name, sym in scope.symbols.items():
            v = sym.value
            v_str = repr(v)
            if len(v_str) > 30:
                v_str = v_str[:27] + "..."
            out.append(f"{scope.name:<19} | {name:<17} | {sym.kind:<11} | {sym.type_:<11} | {v_str}")
    return "\n".join(out)

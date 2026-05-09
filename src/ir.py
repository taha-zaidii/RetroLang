"""
RetroLang intermediate representation (Phase 4).

Two complementary IRs:
  1. GameIR — a structured, typed object graph (the "high-level" IR)
     describing the entire game. This is what the optimizer rewrites and
     the code generator consumes.
  2. TAC    — a flat list of three-address-code quadruples that mirror
     the GameIR construction. The TAC exists primarily for course
     deliverable purposes (visible via --debug) so the grader can see a
     classical IR. Real compilation goes through GameIR.

Quad form:  (op, arg1, arg2, dest)
  e.g. ('SET',     'grid_w', 10,    None)
       ('PIECE',   'I',      [[1,1,1,1]], '#00FFFF')
       ('RULE',    'gravity_speed', 500, None)
       ('BIND',    'move_left',     'KEY_LEFT', None)
       ('CONST',   400,      None,  't1')   -> for arithmetic folding
       ('ADD',     't1', 't2', 't3')
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .ast_nodes import Program


@dataclass
class PieceIR:
    name: str
    shape: List[List[int]]
    color: str  # "#RRGGBB"


@dataclass
class GameIR:
    name: str = ""
    mode: str = "tetris"          # 'tetris' | 'snake'
    grid_w: int = 0
    grid_h: int = 0
    block_size: int = 24
    background: str = "#000000"
    theme: str = "DEFAULT"

    # Tetris-only
    pieces: List[PieceIR] = field(default_factory=list)
    gravity_speed: int = 500
    speedup_every: int = 10
    score_per_line: int = 100
    bonus_tetris: int = 0

    # Snake-only
    start_length: int = 3
    food_count: int = 1
    wrap_edges: bool = False
    snake_speed: int = 200
    score_per_food: int = 10

    # Common
    game_over_conditions: List[str] = field(default_factory=list)
    controls: Dict[str, str] = field(default_factory=dict)  # action -> KEY_*

    # Telemetry from optimizations (used by --debug)
    optimization_log: List[str] = field(default_factory=list)


Quad = Tuple[str, Any, Any, Any]


def lower(program: Program) -> Tuple[GameIR, List[Quad]]:
    """Lower the AST into a GameIR plus a parallel TAC stream."""
    ir = GameIR()
    tac: List[Quad] = []

    h = program.header
    ir.name = h.name
    ir.mode = program.game_mode
    ir.grid_w = h.grid_w
    ir.grid_h = h.grid_h
    ir.block_size = h.block_size
    ir.background = h.background
    ir.theme = h.theme

    tac.append(("HEADER", "name", h.name, None))
    tac.append(("SET", "mode", ir.mode, None))
    tac.append(("SET", "grid_w", h.grid_w, None))
    tac.append(("SET", "grid_h", h.grid_h, None))
    tac.append(("SET", "block_size", h.block_size, None))
    tac.append(("SET", "background", h.background, None))
    tac.append(("SET", "theme", h.theme, None))

    if program.pieces:
        for p in program.pieces.pieces:
            ir.pieces.append(PieceIR(name=p.name, shape=p.shape, color=p.color))
            tac.append(("PIECE", p.name, p.shape, p.color))

    if program.snake_mode:
        s = program.snake_mode
        ir.start_length = s.start_length
        ir.food_count = s.food_count
        ir.wrap_edges = s.wrap_edges
        ir.snake_speed = s.speed_ms
        tac.append(("SNAKE_PROP", "start_length", s.start_length, None))
        tac.append(("SNAKE_PROP", "food_count", s.food_count, None))
        tac.append(("SNAKE_PROP", "wrap_edges", s.wrap_edges, None))
        tac.append(("SNAKE_PROP", "speed", s.speed_ms, None))

    if program.rules:
        for r in program.rules.rules:
            tac.append(("RULE", r.key, r.value, None))
            if r.key == "gravity_speed":
                ir.gravity_speed = r.value
            elif r.key == "speedup_every":
                ir.speedup_every = r.value
            elif r.key == "score_per_line":
                ir.score_per_line = r.value
            elif r.key == "score_per_food":
                ir.score_per_food = r.value
            elif r.key == "bonus_tetris":
                ir.bonus_tetris = r.value
            elif r.key == "game_over":
                ir.game_over_conditions.append(r.value)

    if program.controls:
        for b in program.controls.bindings:
            ir.controls[b.action] = b.key
            tac.append(("BIND", b.action, b.key, None))

    return ir, tac


def format_tac(tac: List[Quad]) -> str:
    out = []
    for i, (op, a, b, c) in enumerate(tac):
        a_s = repr(a) if a is not None else "_"
        b_s = repr(b) if b is not None else "_"
        c_s = repr(c) if c is not None else "_"
        out.append(f"  {i:3}: ({op:<10}, {a_s}, {b_s}, {c_s})")
    return "\n".join(out)


def format_game_ir(ir: GameIR) -> str:
    out = [f"GameIR(name={ir.name!r}, mode={ir.mode!r})"]
    out.append(f"  grid     : {ir.grid_w} x {ir.grid_h}, block={ir.block_size}px")
    out.append(f"  visuals  : background={ir.background}, theme={ir.theme}")
    if ir.mode == "tetris":
        out.append(f"  rules    : gravity={ir.gravity_speed}ms, speedup_every={ir.speedup_every} lines")
        out.append(f"             score_per_line={ir.score_per_line}, bonus_tetris={ir.bonus_tetris}")
        out.append(f"  pieces   ({len(ir.pieces)}):")
        for p in ir.pieces:
            out.append(f"    - {p.name:<3} shape={p.shape} color={p.color}")
    else:
        out.append(f"  snake    : start_length={ir.start_length}, food_count={ir.food_count}")
        out.append(f"             wrap_edges={ir.wrap_edges}, speed={ir.snake_speed}ms")
        out.append(f"             score_per_food={ir.score_per_food}")
    out.append(f"  game_over: {ir.game_over_conditions}")
    out.append(f"  controls : {ir.controls}")
    if ir.optimization_log:
        out.append("  optimization_log:")
        for line in ir.optimization_log:
            out.append(f"    - {line}")
    return "\n".join(out)

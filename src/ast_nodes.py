"""
RetroLang AST node definitions.

These dataclasses are produced by the parser (Phase 2) and consumed by
the semantic analyzer (Phase 3) and IR generator (Phase 4). Each node
carries line/col so later phases can report errors precisely.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any


@dataclass
class Node:
    line: int = 0
    col: int = 0


@dataclass
class GameHeader(Node):
    name: str = ""
    grid_w: int = 0
    grid_h: int = 0
    block_size: int = 24
    background: str = "#000000"
    theme: str = "DEFAULT"


@dataclass
class PieceDef(Node):
    name: str = ""
    shape: List[List[int]] = field(default_factory=list)
    color: str = "#FFFFFF"


@dataclass
class PiecesBlock(Node):
    pieces: List[PieceDef] = field(default_factory=list)


@dataclass
class SnakeModeBlock(Node):
    start_length: int = 3
    food_count: int = 1
    wrap_edges: bool = False
    speed_ms: int = 200


@dataclass
class RuleStmt(Node):
    """Generic rule: (key, value). Value may be int, str, or a list of strs."""
    key: str = ""
    value: Any = None


@dataclass
class RulesBlock(Node):
    rules: List[RuleStmt] = field(default_factory=list)


@dataclass
class ControlBinding(Node):
    action: str = ""
    key: str = ""


@dataclass
class ControlsBlock(Node):
    bindings: List[ControlBinding] = field(default_factory=list)


@dataclass
class Program(Node):
    header: Optional[GameHeader] = None
    pieces: Optional[PiecesBlock] = None
    snake_mode: Optional[SnakeModeBlock] = None
    rules: Optional[RulesBlock] = None
    controls: Optional[ControlsBlock] = None

    @property
    def game_mode(self) -> str:
        """Returns the inferred game mode: 'tetris' or 'snake'."""
        return "snake" if self.snake_mode is not None else "tetris"


def dump(node, indent=0) -> str:
    """Pretty-printer used by --debug to display the AST."""
    pad = "  " * indent
    if isinstance(node, Program):
        out = [f"{pad}Program(mode={node.game_mode})"]
        if node.header:
            out.append(dump(node.header, indent + 1))
        if node.pieces:
            out.append(dump(node.pieces, indent + 1))
        if node.snake_mode:
            out.append(dump(node.snake_mode, indent + 1))
        if node.rules:
            out.append(dump(node.rules, indent + 1))
        if node.controls:
            out.append(dump(node.controls, indent + 1))
        return "\n".join(out)
    if isinstance(node, GameHeader):
        return (f"{pad}GameHeader name={node.name!r} grid={node.grid_w}x{node.grid_h} "
                f"block_size={node.block_size} bg={node.background} theme={node.theme}")
    if isinstance(node, PiecesBlock):
        out = [f"{pad}PiecesBlock"]
        for p in node.pieces:
            out.append(dump(p, indent + 1))
        return "\n".join(out)
    if isinstance(node, PieceDef):
        return f"{pad}PieceDef name={node.name} shape={node.shape} color={node.color}"
    if isinstance(node, SnakeModeBlock):
        return (f"{pad}SnakeModeBlock start_length={node.start_length} "
                f"food_count={node.food_count} wrap_edges={node.wrap_edges} "
                f"speed={node.speed_ms}ms")
    if isinstance(node, RulesBlock):
        out = [f"{pad}RulesBlock"]
        for r in node.rules:
            out.append(dump(r, indent + 1))
        return "\n".join(out)
    if isinstance(node, RuleStmt):
        return f"{pad}RuleStmt {node.key} = {node.value!r}"
    if isinstance(node, ControlsBlock):
        out = [f"{pad}ControlsBlock"]
        for b in node.bindings:
            out.append(dump(b, indent + 1))
        return "\n".join(out)
    if isinstance(node, ControlBinding):
        return f"{pad}ControlBinding {node.action} -> {node.key}"
    return f"{pad}{node!r}"

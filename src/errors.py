"""
RetroLang error reporting.

Centralizes the diagnostic format used by every compiler phase so that
all errors look identical to the end user: phase, line, column, message,
and a caret pointer at the offending source position.
"""

from dataclasses import dataclass


class RetroError(Exception):
    """Base class for any RetroLang compilation error."""

    def __init__(self, phase: str, message: str, line: int = 0, col: int = 0,
                 source_line: str = ""):
        self.phase = phase
        self.message = message
        self.line = line
        self.col = col
        self.source_line = source_line
        super().__init__(self.formatted())

    def formatted(self) -> str:
        header = f"[{self.phase} error] line {self.line}, col {self.col}: {self.message}"
        if not self.source_line:
            return header
        caret = " " * max(self.col - 1, 0) + "^"
        return f"{header}\n    {self.source_line}\n    {caret}"


class LexError(RetroError):
    def __init__(self, msg, line, col, source_line=""):
        super().__init__("Lexical", msg, line, col, source_line)


class ParseError(RetroError):
    def __init__(self, msg, line, col, source_line=""):
        super().__init__("Syntax", msg, line, col, source_line)


class SemanticError(RetroError):
    def __init__(self, msg, line, col, source_line=""):
        super().__init__("Semantic", msg, line, col, source_line)


@dataclass
class SourceContext:
    """Holds the source so error reporters can quote the offending line."""
    text: str

    def line_at(self, line_no: int) -> str:
        lines = self.text.splitlines()
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1]
        return ""

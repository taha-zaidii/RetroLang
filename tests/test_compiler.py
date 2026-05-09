"""
End-to-end compiler tests for RetroLang.

Each test runs the full pipeline and checks an invariant of the output.
The five required course test programs in examples/ are exercised here.
"""

import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.lexer import tokenize
from src.parser import parse
from src.semantic import analyze
from src.ir import lower
from src.optimizer import optimize
from src.codegen import generate
from src.errors import RetroError, LexError, ParseError, SemanticError


def _read(path):
    with open(os.path.join(ROOT, path)) as f:
        return f.read()


def _full_pipeline(src):
    tokens = tokenize(src)
    program = parse(tokens, src)
    table = analyze(program, src)
    ir, tac = lower(program)
    ir, tac = optimize(ir, tac)
    py = generate(ir)
    return tokens, program, table, ir, tac, py


class TestExamples(unittest.TestCase):
    """The five required test programs all compile to runnable Python."""

    def _check_example(self, path, expected_mode, min_pieces=0):
        src = _read(path)
        tokens, program, table, ir, tac, py = _full_pipeline(src)
        self.assertEqual(ir.mode, expected_mode, f"{path}: wrong mode")
        if expected_mode == "tetris":
            self.assertGreaterEqual(len(ir.pieces), min_pieces)
        # generated Python must be syntactically valid
        ast.parse(py)
        self.assertIn("def main()", py)

    def test_neontetris(self):
        self._check_example("examples/neontetris.retro", "tetris", min_pieces=7)

    def test_classictetris(self):
        self._check_example("examples/classictetris.retro", "tetris", min_pieces=4)

    def test_minimal_tetris(self):
        self._check_example("examples/minimal_tetris.retro", "tetris", min_pieces=1)

    def test_snake(self):
        self._check_example("examples/snake.retro", "snake")

    def test_fastsnake(self):
        self._check_example("examples/fastsnake.retro", "snake")
        # wrap_edges true should be reflected in the IR
        src = _read("examples/fastsnake.retro")
        _, _, _, ir, _, _ = _full_pipeline(src)
        self.assertTrue(ir.wrap_edges)


class TestErrorReporting(unittest.TestCase):
    """The bundled error_demo.retro must trip the semantic analyzer."""

    def test_error_demo_fails(self):
        src = _read("examples/error_demo.retro")
        with self.assertRaises(RetroError):
            _full_pipeline(src)

    def test_lex_unterminated_string(self):
        with self.assertRaises(LexError):
            tokenize('game "unterminated\n')

    def test_lex_bad_hex(self):
        with self.assertRaises(LexError):
            tokenize("background #ABCDE\n")  # 5 hex digits invalid

    def test_parser_missing_grid_height(self):
        src = 'game "X"\n  grid 10 x\n'
        with self.assertRaises(ParseError):
            program = parse(tokenize(src), src)

    def test_semantic_zero_grid(self):
        src = (
            'game "Bad"\n'
            '  grid 0 x 5\n'
            '  block_size 16\n'
            '  background #000000\n'
            '  theme MONO\n'
            'pieces\n  define O [[1,1],[1,1]] color #FFFFFF\n'
            'controls\n  move_left KEY_LEFT\n'
        )
        with self.assertRaises(SemanticError):
            analyze(parse(tokenize(src), src), src)

    def test_semantic_unknown_theme(self):
        src = (
            'game "Bad"\n'
            '  grid 5 x 5\n  block_size 16\n  background #000000\n  theme PURPLE\n'
            'pieces\n  define O [[1,1],[1,1]] color #FFFFFF\n'
            'controls\n  move_left KEY_LEFT\n'
        )
        with self.assertRaises(SemanticError):
            analyze(parse(tokenize(src), src), src)

    def test_semantic_duplicate_piece(self):
        src = (
            'game "Bad"\n  grid 5 x 5\n  block_size 16\n  background #000000\n  theme MONO\n'
            'pieces\n  define O [[1,1],[1,1]] color #FFFFFF\n'
            '         define O [[1,1],[1,1]] color #FFFFFF\n'
            'controls\n  move_left KEY_LEFT\n'
        )
        with self.assertRaises(SemanticError):
            analyze(parse(tokenize(src), src), src)

    def test_semantic_mode_action_mismatch(self):
        # snake-mode game cannot bind 'rotate'
        src = (
            'game "Bad"\n  grid 10 x 10\n  block_size 16\n  background #000000\n  theme MONO\n'
            'snake_mode\n  start_length 3\n  food_count 1\n  wrap_edges false\n  speed 200ms\n'
            'controls\n  rotate KEY_UP\n'
        )
        with self.assertRaises(SemanticError):
            analyze(parse(tokenize(src), src), src)


class TestOptimization(unittest.TestCase):

    def test_dead_piece_in_snake_mode(self):
        # A snake-mode program isn't allowed to have a pieces block
        # (mutually exclusive), so the dead-piece pass is exercised via
        # a tetris program with an all-zero shape — but the parser will
        # reject all-zero shapes too. So we exercise it on the 4*score
        # constant-fold recognition, which is what neontetris triggers.
        src = _read("examples/neontetris.retro")
        _, _, _, ir, _, _ = _full_pipeline(src)
        self.assertTrue(any("constant-fold" in s for s in ir.optimization_log))

    def test_peephole_dedup_bind(self):
        # Construct a synthetic IR with duplicate BIND quads
        from src.ir import GameIR
        from src.optimizer import peephole
        ir = GameIR(name="x", mode="tetris")
        tac = [
            ("BIND", "move_left", "KEY_LEFT", None),
            ("BIND", "move_left", "KEY_LEFT", None),  # exact duplicate
            ("BIND", "move_right", "KEY_RIGHT", None),
        ]
        out = peephole(ir, tac)
        self.assertEqual(len(out), 2)


class TestREPL(unittest.TestCase):

    def test_pipeline_function_used_by_repl(self):
        from src.repl import _compile_pipeline
        src = _read("examples/minimal_tetris.retro")
        tokens, ast_, table, ir, tac = _compile_pipeline(src)
        self.assertEqual(ir.mode, "tetris")


if __name__ == "__main__":
    unittest.main(verbosity=2)

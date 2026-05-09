#!/usr/bin/env python3
"""
RetroLang compiler — command-line entry point.

Usage:
    python retrolang.py <input.retro>                 # compile + launch
    python retrolang.py <input.retro> -o <out.py>     # emit Python only
    python retrolang.py <input.retro> --emit-python   # write <input>.py
    python retrolang.py <input.retro> --debug         # full phase trace
    python retrolang.py <input.retro> --no-run        # compile but don't launch
    python retrolang.py --interactive                 # REPL mode

The CLI is intentionally thin: every phase is invoked from the modules
in src/, and errors propagate as RetroError subclasses with line/col.
"""

import argparse
import os
import sys
import importlib.util
import tempfile

# Ensure the local `src` package is importable when this file is run
# directly from the project directory.
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from src.lexer import tokenize, format_tokens
from src.parser import parse
from src.semantic import analyze, format_symbol_table
from src.ir import lower, format_tac, format_game_ir
from src.optimizer import optimize, format_optimization_diff
from src.codegen import generate
from src.ast_nodes import dump as dump_ast
from src.errors import RetroError
from src.repl import run_repl


def _section(title: str):
    bar = "=" * 70
    return f"\n{bar}\n  {title}\n{bar}"


def compile_source(source: str, debug: bool = False) -> str:
    """Run all six compiler phases and return generated Python source.

    When debug is True, prints a phase-by-phase trace to stdout.
    """
    if debug:
        print(_section("Phase 1: Lexical Analysis"))
    tokens = tokenize(source)
    if debug:
        print(format_tokens(tokens))

    if debug:
        print(_section("Phase 2: Syntax Analysis (AST)"))
    ast = parse(tokens, source)
    if debug:
        print(dump_ast(ast))

    if debug:
        print(_section("Phase 3: Semantic Analysis (Symbol Table)"))
    table = analyze(ast, source)
    if debug:
        print(format_symbol_table(table))

    if debug:
        print(_section("Phase 4: IR Generation (TAC + GameIR)"))
    ir, tac = lower(ast)
    if debug:
        print("[unoptimized GameIR]")
        print(format_game_ir(ir))
        print("\n[unoptimized TAC]")
        print(format_tac(tac))

    before_tac = list(tac)
    if debug:
        print(_section("Phase 5: Optimization"))
    ir, tac = optimize(ir, tac)
    if debug:
        print(format_optimization_diff(before_tac, tac))
        if ir.optimization_log:
            print("[optimization log]")
            for line in ir.optimization_log:
                print(f"  - {line}")
        print("\n[optimized GameIR]")
        print(format_game_ir(ir))
        print("\n[optimized TAC]")
        print(format_tac(tac))

    if debug:
        print(_section("Phase 6: Code Generation"))
    py_source = generate(ir)
    if debug:
        print(f"(generated {len(py_source.splitlines())} lines of Python; "
              f"--emit-python to save it)")
    return py_source


def run_module(py_source: str):
    """Execute the generated Python in-process."""
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("[runtime] pygame is not installed.", file=sys.stderr)
        print("[runtime] Install it with:  pip install pygame", file=sys.stderr)
        print("[runtime] Or rerun with --emit-python to skip launching.", file=sys.stderr)
        sys.exit(2)

    # macOS: ensure the SDL window surfaces correctly even when launched
    # from a plain terminal (not a .app bundle).  These vars must be set
    # *before* pygame.init() is called inside the generated module.
    import platform
    if platform.system() == "Darwin":
        os.environ.setdefault("SDL_VIDEO_MAC_FULLSCREEN_SPACES", "0")
        # Force SDL to use the Quartz/Cocoa video driver so a visible
        # window is always created; "offscreen" would suppress it.
        os.environ.pop("SDL_VIDEODRIVER", None)

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(py_source)
        path = f.name
    spec = importlib.util.spec_from_file_location("__retrolang_compiled__", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="retrolang",
        description="RetroLang compiler — compiles .retro arcade games to Python/pygame.",
    )
    p.add_argument("input", nargs="?", help=".retro source file")
    p.add_argument("-o", "--output", help="write generated Python to this file (skip launch)")
    p.add_argument("--emit-python", action="store_true",
                   help="write generated Python next to the source as <name>.py")
    p.add_argument("--debug", action="store_true",
                   help="print every compiler phase (tokens, AST, symbols, IR, TAC, opt log)")
    p.add_argument("--no-run", action="store_true",
                   help="compile only, don't launch the game window")
    p.add_argument("--interactive", action="store_true", help="start REPL mode")
    args = p.parse_args(argv)

    if args.interactive:
        run_repl()
        return 0

    if not args.input:
        p.print_help(); return 1

    try:
        with open(args.input) as f:
            source = f.read()
    except OSError as e:
        print(f"error: cannot read {args.input}: {e}", file=sys.stderr)
        return 1

    try:
        py_source = compile_source(source, debug=args.debug)
    except RetroError as e:
        print(e, file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w") as f:
            f.write(py_source)
        print(f"[ok] wrote generated Python to {args.output}")
        return 0

    if args.emit_python:
        base = os.path.splitext(args.input)[0]
        out_path = base + ".py"
        with open(out_path, "w") as f:
            f.write(py_source)
        print(f"[ok] wrote generated Python to {out_path}")

    if args.no_run:
        return 0

    run_module(py_source)
    return 0


if __name__ == "__main__":
    sys.exit(main())

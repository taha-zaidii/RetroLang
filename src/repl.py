"""
RetroLang REPL — interactive snippet tester.

The REPL accepts:
  * a complete .retro program (multi-line; terminate with a blank line
    or 'run')
  * the meta-commands  :tokens   :ast   :symbols   :ir   :tac   :opt
                       :load <file>   :game-select   :quit   :help
A snippet is compiled to GameIR but is not run unless the user types
'run' (which then launches the pygame window via the code generator).
"""

import os
import sys
import importlib.util
import tempfile

from .lexer import tokenize, format_tokens
from .parser import parse
from .semantic import analyze, format_symbol_table
from .ir import lower, format_tac, format_game_ir
from .optimizer import optimize
from .codegen import generate
from .ast_nodes import dump as dump_ast
from .errors import RetroError


BANNER = r"""
   ____      _             _
  |  _ \ ___| |_ _ __ ___ | |    __ _ _ __   __ _
  | |_) / _ \ __| '__/ _ \| |   / _` | '_ \ / _` |
  |  _ <  __/ |_| | | (_) | |__| (_| | | | | (_| |
  |_| \_\___|\__|_|  \___/|_____\__,_|_| |_|\__, |
                                            |___/
   RetroLang v1.0  —  retro arcade compiler REPL
   Type :help for commands, paste a program, or :load a file.
"""

HELP = """\
Meta commands:
  :tokens       show tokens for current buffer
  :ast          show parsed AST
  :symbols      show symbol table
  :ir           show GameIR (after optimizations)
  :tac          show TAC (after optimizations)
  :opt          show optimization log
  :load <file>  load a .retro source file into the buffer
  :game-select  pick from examples/ and run it (Choose-Your-Own-Adventure)
  :clear        empty the buffer
  :show         print the current buffer
  :run          compile + launch the game
  :quit         exit the REPL
  :help         this message

Anything else is appended to the buffer. Try:

    game "Demo"
        grid 5 x 5
        block_size 24
        background #000000
        theme MONO

    pieces
        define O [[1,1],[1,1]] color #FFFFFF

    rules
        gravity_speed 500ms
        score_per_line 100
        game_over on_top_collision

    controls
        move_left  KEY_LEFT
        move_right KEY_RIGHT
        rotate     KEY_UP
        soft_drop  KEY_DOWN
        hard_drop  KEY_SPACE
        pause      KEY_P
"""


def _compile_pipeline(src: str):
    """Run the full pipeline and return (tokens, ast, table, ir, tac)."""
    tokens = tokenize(src)
    ast = parse(tokens, src)
    table = analyze(ast, src)
    ir, tac = lower(ast)
    ir, tac = optimize(ir, tac)
    return tokens, ast, table, ir, tac


def _run_generated(py_source: str):
    """Write generated code to a temp file and exec it."""
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("[runtime] pygame is not installed. Install it with:")
        print("          pip install pygame")
        return
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(py_source)
        path = f.name
    spec = importlib.util.spec_from_file_location("__retrolang_compiled__", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass


def _list_examples():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ex_dir = os.path.join(here, "examples")
    if not os.path.isdir(ex_dir):
        return []
    return sorted(f for f in os.listdir(ex_dir) if f.endswith(".retro"))


def run_repl():
    print(BANNER)
    buffer = ""
    examples_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples",
    )

    while True:
        try:
            prompt = "retro> " if not buffer else "  ...> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return

        stripped = line.strip()
        if not stripped:
            continue

        if stripped == ":quit" or stripped == ":exit":
            return
        if stripped == ":help":
            print(HELP); continue
        if stripped == ":clear":
            buffer = ""; print("(buffer cleared)"); continue
        if stripped == ":show":
            print(buffer or "(empty)"); continue
        if stripped == ":game-select":
            examples = _list_examples()
            if not examples:
                print("(no examples found)"); continue
            print("Available retro games:")
            for i, name in enumerate(examples, 1):
                print(f"  {i}. {name}")
            try:
                choice = input("Select [1-{}]: ".format(len(examples))).strip()
                idx = int(choice) - 1
                if not (0 <= idx < len(examples)):
                    print("(invalid selection)"); continue
            except (ValueError, EOFError, KeyboardInterrupt):
                print(); continue
            target = os.path.join(examples_dir, examples[idx])
            with open(target) as f:
                buffer = f.read()
            print(f"(loaded {examples[idx]} — type :run to launch)")
            continue
        if stripped.startswith(":load"):
            parts = stripped.split(maxsplit=1)
            if len(parts) != 2:
                print("usage: :load <path>"); continue
            try:
                with open(parts[1]) as f:
                    buffer = f.read()
                print(f"(loaded {parts[1]})")
            except OSError as e:
                print(f"error: {e}")
            continue

        if stripped in (":tokens", ":ast", ":symbols", ":ir", ":tac", ":opt", ":run"):
            if not buffer.strip():
                print("(buffer is empty)"); continue
            try:
                tokens, ast, table, ir, tac = _compile_pipeline(buffer)
            except RetroError as e:
                print(e); continue
            if stripped == ":tokens":
                print(format_tokens(tokens))
            elif stripped == ":ast":
                print(dump_ast(ast))
            elif stripped == ":symbols":
                print(format_symbol_table(table))
            elif stripped == ":ir":
                print(format_game_ir(ir))
            elif stripped == ":tac":
                print(format_tac(tac))
            elif stripped == ":opt":
                if ir.optimization_log:
                    for line in ir.optimization_log:
                        print(f"  - {line}")
                else:
                    print("(no optimizations applied)")
            elif stripped == ":run":
                py_src = generate(ir)
                _run_generated(py_src)
            continue

        # otherwise append to buffer
        buffer += line + "\n"

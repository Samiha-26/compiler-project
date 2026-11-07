"""Compiler driver and command-line interface implementation."""

from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional

from cminor import __version__
from cminor.diagnostics import (
    DiagnosticCode,
    DiagnosticEmitter,
    CompilerException,
)
from cminor.lexer import Lexer, TokenType
from cminor.parser import Parser, ASTDumper
from cminor.sema import SemanticAnalyzer
from cminor.ir import IRGenerator
from cminor.codegen import LLVMEmitter, QBEEmitter


CAPABILITIES_TEXT = f"""C Minor Compiler (cminorcc) Capabilities Report
=================================================
Language Version: C Minor 1.0 (course-defined profile, SRS 1.0)
Compiler Version: {__version__}
Target: Linux x86-64 (System V AMD64 ABI, ELF)
Supported Backends: llvm (LLVM llc), qbe (QBE qbe)
Default Backend: llvm

Accepted Source Forms:
  - Extensions: .cm, .c
  - Scalar Types: signed 32-bit int
  - Return Types: int, void
  - Parameter Count: 0 to 6 int parameters
  - Preprocessing: DISABLED (directives like #include, #define, %: raise UNSUPPORTED_PREPROCESSING_DIRECTIVE)
  - Line Splicing: DISABLED (backslash before newline raises UNSUPPORTED_LINE_SPLICING)

Resource Limits (Baseline Minima):
  - Max Input File Size: 32 KiB (4,000 tokens)
  - Max Block Nesting: 16 levels
  - Max Expression Nesting: 16 levels
  - Max User Functions: 32 per translation unit
  - Max Locals per Block: 64 local declarations
  - Max Line Length: 2,048 characters

Optional Extensions:
  - Dual Backend Support: Both LLVM and QBE IL lowering implemented
"""


class DriverArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that reports errors with exit code 2 and COMMAND_ERROR."""

    def error(self, message: str) -> None:
        sys.stderr.write(f"cminorcc: error: [{DiagnosticCode.COMMAND_ERROR.value}] {message}\n")
        sys.exit(2)


def create_argument_parser() -> DriverArgumentParser:
    parser = DriverArgumentParser(
        prog="cminorcc",
        description="C Minor Compiler - course project compiler for C Minor.",
        add_help=False,
    )

    parser.add_argument("source_file", nargs="?", help="Input C Minor source file (.cm or .c)")
    parser.add_argument("-o", "--output", dest="output", help="Output file path")
    parser.add_argument("--check", action="store_true", help="Run semantic checks only, do not emit assembly")
    parser.add_argument("--dump-tokens", action="store_true", help="Print scanned tokens to stdout")
    parser.add_argument("--dump-ast", action="store_true", help="Print abstract syntax tree to stdout")
    parser.add_argument("--dump-symbols", action="store_true", help="Print symbol table to stdout")
    parser.add_argument("--dump-ir", action="store_true", help="Print student IR to stdout")
    parser.add_argument("--emit-backend-ir", action="store_true", help="Emit backend intermediate representation")
    parser.add_argument("--backend", choices=["llvm", "qbe"], default="llvm", help="Select native backend (default: llvm)")
    parser.add_argument("--capabilities", action="store_true", help="Report compiler capabilities and limits")
    parser.add_argument("-v", "--version", action="store_true", help="Display compiler version")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")

    return parser


class CompilerDriver:
    """Coordinates compilation phases according to command line options."""

    def __init__(self, emitter: Optional[DiagnosticEmitter] = None) -> None:
        self.emitter = emitter or DiagnosticEmitter(sys.stderr)

    def run(self, argv: List[str]) -> int:
        parser = create_argument_parser()
        args = parser.parse_args(argv)

        # Handle informative options first
        if args.help:
            parser.print_help(sys.stdout)
            return 0

        if args.version:
            print(f"cminorcc version {__version__}")
            return 0

        if args.capabilities:
            print(CAPABILITIES_TEXT.strip())
            return 0

        # Require a source file if not requesting information
        if not args.source_file:
            self.emitter.report(
                code=DiagnosticCode.COMMAND_ERROR,
                message="No input source file specified.",
            )
            return 2

        # Validate file extension
        _, ext = os.path.splitext(args.source_file)
        if ext not in [".cm", ".c"]:
            self.emitter.report(
                code=DiagnosticCode.COMMAND_ERROR,
                message=f"Invalid source file extension '{ext}'. Expected .cm or .c.",
            )
            return 2

        # Verify mutual exclusivity of stage dump / check actions (CM-CLI-003)
        actions = [
            args.check,
            args.dump_tokens,
            args.dump_ast,
            args.dump_symbols,
            args.dump_ir,
            args.emit_backend_ir,
        ]
        if sum(1 for a in actions if a) > 1:
            self.emitter.report(
                code=DiagnosticCode.COMMAND_ERROR,
                message="Stage dumps, --check, and --emit-backend-ir are mutually exclusive.",
            )
            return 2

        # Verify source file existence and readability (CM-DIA-002, IO_ERROR)
        if not os.path.exists(args.source_file):
            self.emitter.report(
                code=DiagnosticCode.IO_ERROR,
                message=f"Cannot open source file '{args.source_file}': No such file or directory.",
            )
            return 1

        try:
            with open(args.source_file, "r", encoding="utf-8") as f:
                source_code = f.read()
        except UnicodeDecodeError:
            self.emitter.report(
                code=DiagnosticCode.LEXICAL_ERROR,
                message=f"Source file '{args.source_file}' contains invalid non-UTF-8 characters.",
            )
            return 1
        except OSError as e:
            self.emitter.report(
                code=DiagnosticCode.IO_ERROR,
                message=f"Failed to read source file '{args.source_file}': {e.strerror}",
            )
            return 1

        # Determine default output file if -o is not provided (CM-CLI-001)
        base_name, _ = os.path.splitext(args.source_file)
        if args.output:
            output_path = args.output
        else:
            output_path = f"{base_name}.s"

        return self.compile(
            source_file=args.source_file,
            source_code=source_code,
            output_path=output_path,
            args=args,
        )

    def compile(self, source_file: str, source_code: str, output_path: str, args: argparse.Namespace) -> int:
        lexer = Lexer(source_code=source_code, file_path=source_file, emitter=self.emitter)
        tokens = lexer.tokenize()

        if self.emitter.has_errors():
            return 1

        if args.dump_tokens:
            for tok in tokens:
                loc = f"{tok.span.start.line}:{tok.span.start.column}"
                if tok.type == TokenType.INT_LITERAL:
                    print(f"{loc:<10} {tok.type.name:<15} '{tok.lexeme}' (value={tok.value})")
                elif tok.type == TokenType.EOF:
                    print(f"{loc:<10} {tok.type.name}")
                else:
                    print(f"{loc:<10} {tok.type.name:<15} '{tok.lexeme}'")
            return 0

        parser = Parser(tokens=tokens, file_path=source_file, emitter=self.emitter)
        ast = parser.parse_program()

        if self.emitter.has_errors():
            return 1

        if args.dump_ast:
            dumper = ASTDumper()
            print(dumper.dump(ast))
            return 0

        analyzer = SemanticAnalyzer(emitter=self.emitter)
        analyzer.analyze(ast)

        if self.emitter.has_errors():
            return 1

        if args.dump_symbols:
            print(analyzer.dump_symbols())
            return 0

        if args.check:
            return 0

        ir_gen = IRGenerator()
        ir_program = ir_gen.generate(ast)

        if args.dump_ir:
            print(ir_program.format())
            return 0

        backend_name = args.backend
        if backend_name == "llvm":
            llvm_emitter = LLVMEmitter()
            backend_ir_text = llvm_emitter.emit(ir_program)
            il_ext = ".ll"
        elif backend_name == "qbe":
            qbe_emitter = QBEEmitter()
            backend_ir_text = qbe_emitter.emit(ir_program)
            il_ext = ".ssa"
        else:
            self.emitter.report(
                code=DiagnosticCode.COMMAND_ERROR,
                message=f"Unsupported backend '{backend_name}'. Supported backends: llvm, qbe.",
            )
            return 2

        if args.emit_backend_ir:
            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(backend_ir_text)
                    return 0
                except OSError as e:
                    self.emitter.report(
                        code=DiagnosticCode.IO_ERROR,
                        message=f"Failed to write backend IR to '{args.output}': {e.strerror}",
                    )
                    return 1
            else:
                sys.stdout.write(backend_ir_text)
                return 0

        return self._invoke_backend(
            backend_name=backend_name,
            backend_ir_text=backend_ir_text,
            il_ext=il_ext,
            output_path=output_path,
        )

    def _invoke_backend(
        self,
        backend_name: str,
        backend_ir_text: str,
        il_ext: str,
        output_path: str,
    ) -> int:
        tool_name = "llc" if backend_name == "llvm" else "qbe"
        tool_path = shutil.which(tool_name)
        if not tool_path:
            self.emitter.report(
                code=DiagnosticCode.BACKEND_ERROR,
                message=f"Backend executable '{tool_name}' not found in system PATH.",
            )
            return 1

        out_dir = os.path.dirname(os.path.abspath(output_path))
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                self.emitter.report(
                    code=DiagnosticCode.IO_ERROR,
                    message=f"Cannot create output directory '{out_dir}': {e.strerror}",
                )
                return 1

        temp_ir = None
        temp_s = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=il_ext, delete=False, encoding="utf-8") as f:
                f.write(backend_ir_text)
                temp_ir = f.name

            temp_s = tempfile.mktemp(suffix=".s", dir=out_dir)

            if backend_name == "llvm":
                cmd = [
                    tool_path,
                    "-O0",
                    "-mtriple=x86_64-pc-linux-gnu",
                    "-filetype=asm",
                    temp_ir,
                    "-o",
                    temp_s,
                ]
            else:
                cmd = [
                    tool_path,
                    "-t",
                    "amd64_sysv",
                    "-o",
                    temp_s,
                    temp_ir,
                ]

            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                self.emitter.report(
                    code=DiagnosticCode.BACKEND_ERROR,
                    message=f"Backend '{tool_name}' failed with exit code {proc.returncode}: {proc.stderr.strip()}",
                )
                return 1

            os.replace(temp_s, output_path)
            return 0

        except OSError as e:
            self.emitter.report(
                code=DiagnosticCode.IO_ERROR,
                message=f"File I/O error during backend code emission: {e.strerror}",
            )
            return 1
        finally:
            if temp_ir and os.path.exists(temp_ir):
                try:
                    os.remove(temp_ir)
                except OSError:
                    pass
            if temp_s and os.path.exists(temp_s):
                try:
                    os.remove(temp_s)
                except OSError:
                    pass


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    driver = CompilerDriver()
    return driver.run(argv)


if __name__ == "__main__":
    sys.exit(main())

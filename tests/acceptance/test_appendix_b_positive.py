"""Normative positive acceptance tests from Appendix B (B.1 - B.4)."""

import io
import sys
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.diagnostics import DiagnosticEmitter
from cminor.lexer import Lexer
from cminor.parser import Parser
from cminor.sema import SemanticAnalyzer
from cminor.ir import IRGenerator
from cminor.codegen import LLVMEmitter, QBEEmitter


class TestAppendixBPositive(unittest.TestCase):
    def _run_pipeline(self, src: str):
        stderr_io = io.StringIO()
        emitter = DiagnosticEmitter(stream=stderr_io)

        lexer = Lexer(source_code=src, file_path="acceptance.cm", emitter=emitter)
        tokens = lexer.tokenize()
        self.assertFalse(emitter.has_errors(), f"Lexer error: {stderr_io.getvalue()}")

        parser = Parser(tokens=tokens, file_path="acceptance.cm", emitter=emitter)
        ast = parser.parse_program()
        self.assertFalse(emitter.has_errors(), f"Parser error: {stderr_io.getvalue()}")

        analyzer = SemanticAnalyzer(emitter=emitter)
        self.assertTrue(analyzer.analyze(ast), f"Sema error: {stderr_io.getvalue()}")

        ir_gen = IRGenerator()
        ir_prog = ir_gen.generate(ast)
        self.assertGreater(len(ir_prog.functions), 0)

        llvm_emitter = LLVMEmitter()
        llvm_ir = llvm_emitter.emit(ir_prog)
        self.assertIn("target triple", llvm_ir)

        qbe_emitter = QBEEmitter()
        qbe_il = qbe_emitter.emit(ir_prog)
        self.assertIn("export function", qbe_il)

        return ir_prog, llvm_ir, qbe_il

    def test_b1_precedence_comments_and_local_variables(self) -> None:
        src = """
        int main(void) {
            // A directive-looking #include is just a comment.
            int a = 10; /* a non-nested block comment */
            int/**/b = 2;
            int total = a + b * 3;
            if (total != 16) return 1;
            return 0;
        }
        """
        ir, llvm_ir, qbe_il = self._run_pipeline(src)
        self.assertIn("main", [f.name for f in ir.functions])

    def test_b2_prototypes_and_recursion(self) -> None:
        src = """
        int fact(int n);
        int main(void) {
            if (fact(5) != 120) return 1;
            return 0;
        }
        int fact(int n) {
            if (n <= 1) return 1;
            return n * fact(n - 1);
        }
        """
        ir, llvm_ir, qbe_il = self._run_pipeline(src)
        self.assertEqual(len(ir.functions), 2)

    def test_b3_loops_continue_shadowing_and_short_circuit(self) -> None:
        src = """
        int main(void) {
            int sum = 0;
            int touched = 0;
            for (int i = 1; i <= 5; i = i + 1) {
                if (i == 3) continue;
                { int sum = 9; sum = sum + 1; }
                sum = sum + i;
            }
            if (0 && (touched = 1)) return 1;
            if (1 || (touched = 2)) { ; }
            if (sum != 12) return 1;
            if (touched != 0) return 1;
            return 0;
        }
        """
        ir, llvm_ir, qbe_il = self._run_pipeline(src)
        self.assertIn("main", [f.name for f in ir.functions])

    def test_b4_function_arguments_and_void_functions(self) -> None:
        src = """
        void noop(void) { return; }
        int add(int a, int b) { return a + b; }
        int main(void) {
            noop();
            if (add(19, 23) != 42) return 1;
            return 0;
        }
        """
        ir, llvm_ir, qbe_il = self._run_pipeline(src)
        self.assertEqual(len(ir.functions), 3)


if __name__ == "__main__":
    unittest.main()

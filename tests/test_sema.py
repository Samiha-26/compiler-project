"""Unit tests for C Minor semantic analysis."""

import io
import sys
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.diagnostics import DiagnosticCode, DiagnosticEmitter
from cminor.lexer import Lexer
from cminor.parser import Parser
from cminor.sema import SemanticAnalyzer


class TestSemanticAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.stderr_io = io.StringIO()
        self.emitter = DiagnosticEmitter(stream=self.stderr_io)

    def _analyze(self, src: str):
        lexer = Lexer(source_code=src, file_path="test.cm", emitter=self.emitter)
        tokens = lexer.tokenize()
        parser = Parser(tokens=tokens, file_path="test.cm", emitter=self.emitter)
        ast = parser.parse_program()
        analyzer = SemanticAnalyzer(emitter=self.emitter)
        analyzer.analyze(ast)
        return analyzer, self.emitter.diagnostics

    def test_valid_program_passes(self) -> None:
        src = """
        int add(int a, int b);
        int main(void) {
            int x = add(1, 2);
            return x;
        }
        int add(int a, int b) {
            return a + b;
        }
        """
        _, diags = self._analyze(src)
        self.assertEqual(len(diags), 0)

    def test_missing_main_raises_name_error(self) -> None:
        src = "int foo(void) { return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_invalid_main_signature_raises_type_error(self) -> None:
        src = "void main(void) { return; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.TYPE_ERROR for d in diags))

    def test_undeclared_variable_raises_name_error(self) -> None:
        src = "int main(void) { x = 1; return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_redeclaration_in_same_scope_raises_name_error(self) -> None:
        src = "int main(void) { int x = 5; int x = 6; return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_shadowing_in_inner_block_is_allowed(self) -> None:
        src = """
        int main(void) {
            int x = 5;
            {
                int x = 10;
                x = x + 1;
            }
            return x;
        }
        """
        _, diags = self._analyze(src)
        self.assertEqual(len(diags), 0)

    def test_unresolved_function_declaration_raises_name_error(self) -> None:
        src = "int foo(int a); int main(void) { return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_break_outside_loop_raises_control_flow_error(self) -> None:
        src = "int main(void) { break; return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.CONTROL_FLOW_ERROR for d in diags))

    def test_continue_outside_loop_raises_control_flow_error(self) -> None:
        src = "int main(void) { continue; return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.CONTROL_FLOW_ERROR for d in diags))

    def test_missing_final_top_level_return_in_int_function(self) -> None:
        src = "int main(void) { if (1) return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.RETURN_ERROR for d in diags))

    def test_assign_to_non_lvalue_raises_type_error(self) -> None:
        src = "int main(void) { 5 = 10; return 0; }"
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.TYPE_ERROR for d in diags))

    def test_call_argument_count_mismatch_raises_call_error(self) -> None:
        src = """
        int add(int a, int b) { return a + b; }
        int main(void) { return add(1); }
        """
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.CALL_ERROR for d in diags))

    def test_void_function_returning_value_raises_return_error(self) -> None:
        src = """
        void foo(void) { return 1; }
        int main(void) { return 0; }
        """
        _, diags = self._analyze(src)
        self.assertTrue(any(d.code == DiagnosticCode.RETURN_ERROR for d in diags))


if __name__ == "__main__":
    unittest.main()

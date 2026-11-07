"""Normative negative and boundary test cases from Appendix B.5."""

import io
import sys
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.diagnostics import DiagnosticCode, DiagnosticEmitter
from cminor.lexer import Lexer
from cminor.parser import Parser
from cminor.sema import SemanticAnalyzer


class TestAppendixBNegative(unittest.TestCase):
    def _check_source(self, src: str):
        stderr_io = io.StringIO()
        emitter = DiagnosticEmitter(stream=stderr_io)

        lexer = Lexer(source_code=src, file_path="test_neg.cm", emitter=emitter)
        tokens = lexer.tokenize()
        if emitter.has_errors():
            return emitter.diagnostics

        parser = Parser(tokens=tokens, file_path="test_neg.cm", emitter=emitter)
        ast = parser.parse_program()
        if emitter.has_errors():
            return emitter.diagnostics

        analyzer = SemanticAnalyzer(emitter=emitter)
        analyzer.analyze(ast)
        return emitter.diagnostics

    def test_b5_include_directive(self) -> None:
        src = "#include <stdio.h>\nint main(void) { return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_PREPROCESSING_DIRECTIVE for d in diags))

    def test_b5_digraph_directive(self) -> None:
        src = "%:define X 5\nint main(void) { return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_PREPROCESSING_DIRECTIVE for d in diags))

    def test_b5_valid_comment_with_directive(self) -> None:
        src = "// #include <stdio.h>\nint main(void) { return 0; }"
        diags = self._check_source(src)
        self.assertEqual(len(diags), 0)

    def test_b5_token_separation_across_comment(self) -> None:
        src = "int main(void) { int/**/name = 1; return 0; }"
        diags = self._check_source(src)
        self.assertEqual(len(diags), 0)

    def test_b5_unterminated_comment(self) -> None:
        src = "int main(void) { int x; /* unterminated return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.LEXICAL_ERROR for d in diags))

    def test_b5_hex_literal(self) -> None:
        src = "int main(void) { int x = 0x10; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_literal_out_of_range(self) -> None:
        src = "int main(void) { int x = 2147483648; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_octal_leading_zero(self) -> None:
        src = "int main(void) { int x = 012; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_same_scope_redeclaration(self) -> None:
        src = "int main(void) { int x = 5; int x = 6; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_b5_array_rejected(self) -> None:
        src = "int main(void) { int x[2]; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_float_or_pointer_rejected(self) -> None:
        src = "int main(void) { float x; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_undefined_function_declaration(self) -> None:
        src = "int f(void); int main(void) { return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.NAME_ERROR for d in diags))

    def test_b5_break_outside_loop(self) -> None:
        src = "int main(void) { break; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.CONTROL_FLOW_ERROR for d in diags))

    def test_b5_missing_top_level_final_return(self) -> None:
        src = "int main(void) { if (1) return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.RETURN_ERROR for d in diags))

    def test_b5_unsupported_post_increment(self) -> None:
        src = "int main(void) { int x = 2; x++; return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_b5_int_function_empty_return(self) -> None:
        src = "int main(void) { return; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.RETURN_ERROR for d in diags))

    def test_b5_void_function_value_return(self) -> None:
        src = "void f(void) { return 1; } int main(void) { return 0; }"
        diags = self._check_source(src)
        self.assertTrue(any(d.code == DiagnosticCode.RETURN_ERROR for d in diags))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for C Minor lexical analysis."""

import io
import sys
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.diagnostics import DiagnosticCode, DiagnosticEmitter
from cminor.lexer import Lexer, TokenType


class TestLexer(unittest.TestCase):
    def setUp(self) -> None:
        self.stderr_io = io.StringIO()
        self.emitter = DiagnosticEmitter(stream=self.stderr_io)

    def _tokenize(self, source: str):
        lexer = Lexer(source_code=source, file_path="test.cm", emitter=self.emitter)
        tokens = lexer.tokenize()
        return tokens, self.emitter.diagnostics

    def test_keywords_and_identifiers(self) -> None:
        src = "int void if else while for break continue return foo _bar val123"
        tokens, diags = self._tokenize(src)
        self.assertEqual(len(diags), 0)
        expected = [
            TokenType.KW_INT,
            TokenType.KW_VOID,
            TokenType.KW_IF,
            TokenType.KW_ELSE,
            TokenType.KW_WHILE,
            TokenType.KW_FOR,
            TokenType.KW_BREAK,
            TokenType.KW_CONTINUE,
            TokenType.KW_RETURN,
            TokenType.IDENTIFIER,
            TokenType.IDENTIFIER,
            TokenType.IDENTIFIER,
            TokenType.EOF,
        ]
        self.assertEqual([t.type for t in tokens], expected)
        self.assertEqual(tokens[9].lexeme, "foo")
        self.assertEqual(tokens[10].lexeme, "_bar")
        self.assertEqual(tokens[11].lexeme, "val123")

    def test_integer_literals(self) -> None:
        src = "0 10 2147483647"
        tokens, diags = self._tokenize(src)
        self.assertEqual(len(diags), 0)
        self.assertEqual(tokens[0].value, 0)
        self.assertEqual(tokens[1].value, 10)
        self.assertEqual(tokens[2].value, 2147483647)

    def test_operators_and_punctuators(self) -> None:
        src = "+ - * / % < <= > >= == != ! && || = ( ) { } ; ,"
        tokens, diags = self._tokenize(src)
        self.assertEqual(len(diags), 0)
        types = [t.type for t in tokens]
        self.assertEqual(
            types,
            [
                TokenType.PLUS,
                TokenType.MINUS,
                TokenType.STAR,
                TokenType.SLASH,
                TokenType.PERCENT,
                TokenType.LESS,
                TokenType.LESS_EQUAL,
                TokenType.GREATER,
                TokenType.GREATER_EQUAL,
                TokenType.EQUAL_EQUAL,
                TokenType.BANG_EQUAL,
                TokenType.BANG,
                TokenType.AMP_AMP,
                TokenType.PIPE_PIPE,
                TokenType.ASSIGN,
                TokenType.LPAREN,
                TokenType.RPAREN,
                TokenType.LBRACE,
                TokenType.RBRACE,
                TokenType.SEMICOLON,
                TokenType.COMMA,
                TokenType.EOF,
            ],
        )

    def test_token_boundaries_across_block_comments(self) -> None:
        src = "int/**/b = 2;"
        tokens, diags = self._tokenize(src)
        self.assertEqual(len(diags), 0)
        types = [t.type for t in tokens]
        self.assertEqual(
            types,
            [
                TokenType.KW_INT,
                TokenType.IDENTIFIER,
                TokenType.ASSIGN,
                TokenType.INT_LITERAL,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[1].lexeme, "b")

    def test_comments_ignoring_directives(self) -> None:
        src = "// #include <stdio.h>\n/* %:define X 10 */ int a = 1;"
        tokens, diags = self._tokenize(src)
        self.assertEqual(len(diags), 0)
        self.assertEqual(tokens[0].type, TokenType.KW_INT)

    def test_preprocessing_directive_hash(self) -> None:
        src = "#include <stdio.h>\nint main(void) { return 0; }"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_PREPROCESSING_DIRECTIVE for d in diags))

    def test_preprocessing_directive_digraph(self) -> None:
        src = "%:define FOO 1\nint x;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_PREPROCESSING_DIRECTIVE for d in diags))

    def test_hash_in_middle_of_line_is_lexical_error(self) -> None:
        src = "int x = # 5;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.LEXICAL_ERROR for d in diags))

    def test_line_splicing_rejected(self) -> None:
        src = "int x = \\\n 10;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_LINE_SPLICING for d in diags))

    def test_malformed_integer_hex(self) -> None:
        src = "int x = 0x10;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_malformed_integer_octal_leading_zero(self) -> None:
        src = "int x = 012;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_integer_literal_out_of_range(self) -> None:
        src = "int x = 2147483648;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_unsupported_operators(self) -> None:
        ops = ["++", "--", "+=", "-=", "*=", "/=", "<<", ">>", "?"]
        for op in ops:
            self.setUp()
            src = f"int x {op} 1;"
            _, diags = self._tokenize(src)
            self.assertTrue(
                any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags),
                f"Failed to reject unsupported operator {op}",
            )

    def test_c23_reserved_keywords(self) -> None:
        src = "float x = 1;"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.UNSUPPORTED_FEATURE for d in diags))

    def test_unterminated_block_comment(self) -> None:
        src = "int x; /* unterminated comment"
        _, diags = self._tokenize(src)
        self.assertTrue(any(d.code == DiagnosticCode.LEXICAL_ERROR for d in diags))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for C Minor syntax analysis and AST construction."""

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
from cminor.parser import (
    Parser,
    ASTDumper,
    BinaryExpr,
    AssignExpr,
    IfStmt,
    WhileStmt,
    ForStmt,
    VarDecl,
    FunctionDecl,
    FunctionDef,
)


class TestParser(unittest.TestCase):
    def setUp(self) -> None:
        self.stderr_io = io.StringIO()
        self.emitter = DiagnosticEmitter(stream=self.stderr_io)

    def _parse(self, src: str):
        lexer = Lexer(source_code=src, file_path="test.cm", emitter=self.emitter)
        tokens = lexer.tokenize()
        parser = Parser(tokens=tokens, file_path="test.cm", emitter=self.emitter)
        ast = parser.parse_program()
        return ast, self.emitter.diagnostics

    def test_precedence_arithmetic(self) -> None:
        src = "int main(void) { int x = a + b * c; return 0; }"
        ast, diags = self._parse(src)
        self.assertEqual(len(diags), 0)
        fn = ast.externals[0]
        self.assertIsInstance(fn, FunctionDef)
        decl = fn.body.items[0]
        self.assertIsInstance(decl, VarDecl)
        init = decl.init
        self.assertIsInstance(init, BinaryExpr)
        self.assertEqual(init.op, "+")
        self.assertIsInstance(init.right, BinaryExpr)
        self.assertEqual(init.right.op, "*")

    def test_assignment_associativity(self) -> None:
        src = "int main(void) { a = b = c; return 0; }"
        ast, diags = self._parse(src)
        self.assertEqual(len(diags), 0)
        fn = ast.externals[0]
        stmt = fn.body.items[0]
        assign = stmt.expr
        self.assertIsInstance(assign, AssignExpr)
        self.assertIsInstance(assign.value, AssignExpr)

    def test_dangling_else_attaches_to_closest_if(self) -> None:
        src = """
        int main(void) {
            if (1)
                if (2) x = 1;
                else x = 2;
            return 0;
        }
        """
        ast, diags = self._parse(src)
        self.assertEqual(len(diags), 0)
        outer_if = ast.externals[0].body.items[0]
        self.assertIsInstance(outer_if, IfStmt)
        self.assertIsNone(outer_if.else_branch)
        inner_if = outer_if.then_branch
        self.assertIsInstance(inner_if, IfStmt)
        self.assertIsNotNone(inner_if.else_branch)

    def test_reject_bare_unbraced_declaration(self) -> None:
        # CM-SYN-004: bare unbraced declaration where a statement is expected is invalid
        src = "int main(void) { if (1) int x = 0; return 0; }"
        _, diags = self._parse(src)
        self.assertTrue(any(d.code == DiagnosticCode.SYNTAX_ERROR for d in diags))

    def test_for_loop_with_local_decl_init(self) -> None:
        src = """
        int main(void) {
            for (int i = 0; i < 10; i = i + 1) {
                if (i == 5) break;
            }
            return 0;
        }
        """
        ast, diags = self._parse(src)
        self.assertEqual(len(diags), 0)
        for_stmt = ast.externals[0].body.items[0]
        self.assertIsInstance(for_stmt, ForStmt)
        self.assertIsInstance(for_stmt.init, VarDecl)

    def test_function_prototype_and_definition(self) -> None:
        src = """
        int add(int a, int b);
        int main(void) { return add(1, 2); }
        int add(int a, int b) { return a + b; }
        """
        ast, diags = self._parse(src)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(ast.externals), 3)
        self.assertIsInstance(ast.externals[0], FunctionDecl)
        self.assertIsInstance(ast.externals[1], FunctionDef)
        self.assertIsInstance(ast.externals[2], FunctionDef)


if __name__ == "__main__":
    unittest.main()

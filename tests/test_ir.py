"""Unit tests for C Minor Three-Address Code Intermediate Representation."""

import io
import sys
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.lexer import Lexer
from cminor.parser import Parser
from cminor.sema import SemanticAnalyzer
from cminor.ir import (
    IRGenerator,
    BranchIfZeroInstr,
    BranchIfNotZeroInstr,
    JumpInstr,
    CallInstr,
    ReturnInstr,
    BinOpInstr,
)


class TestIRGenerator(unittest.TestCase):
    def _generate_ir(self, src: str):
        lexer = Lexer(source_code=src, file_path="test.cm")
        tokens = lexer.tokenize()
        parser = Parser(tokens=tokens, file_path="test.cm")
        ast = parser.parse_program()
        analyzer = SemanticAnalyzer()
        self.assertTrue(analyzer.analyze(ast))
        generator = IRGenerator()
        return generator.generate(ast)

    def test_expression_tac(self) -> None:
        src = """
        int main(void) {
            int a = 10;
            int b = 2;
            int c = a + b * 3;
            return c;
        }
        """
        ir = self._generate_ir(src)
        self.assertEqual(len(ir.functions), 1)
        fn = ir.functions[0]
        self.assertEqual(fn.name, "main")
        ops = [instr.op for instr in fn.instructions if isinstance(instr, BinOpInstr)]
        self.assertEqual(ops, ["*", "+"])

    def test_loop_break_continue(self) -> None:
        src = """
        int main(void) {
            int sum = 0;
            for (int i = 0; i < 10; i = i + 1) {
                if (i == 3) continue;
                if (i == 8) break;
                sum = sum + i;
            }
            return sum;
        }
        """
        ir = self._generate_ir(src)
        fn = ir.functions[0]
        has_jump = any(isinstance(instr, JumpInstr) for instr in fn.instructions)
        has_br = any(isinstance(instr, BranchIfZeroInstr) for instr in fn.instructions)
        self.assertTrue(has_jump)
        self.assertTrue(has_br)

    def test_short_circuit_and_or(self) -> None:
        src = """
        int main(void) {
            int a = 0;
            int b = 1;
            int c = a && b;
            int d = a || b;
            return c + d;
        }
        """
        ir = self._generate_ir(src)
        fn = ir.functions[0]
        has_br_zero = any(isinstance(instr, BranchIfZeroInstr) for instr in fn.instructions)
        has_br_nonzero = any(isinstance(instr, BranchIfNotZeroInstr) for instr in fn.instructions)
        self.assertTrue(has_br_zero)
        self.assertTrue(has_br_nonzero)

    def test_recursion_and_calls(self) -> None:
        src = """
        int fact(int n);
        int main(void) {
            return fact(5);
        }
        int fact(int n) {
            if (n <= 1) return 1;
            return n * fact(n - 1);
        }
        """
        ir = self._generate_ir(src)
        self.assertEqual(len(ir.functions), 2)
        fact_fn = ir.functions[1]
        self.assertEqual(fact_fn.name, "fact")
        calls = [instr for instr in fact_fn.instructions if isinstance(instr, CallInstr)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].callee, "fact")


if __name__ == "__main__":
    unittest.main()

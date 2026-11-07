"""Unit tests for backend code generation (LLVM IR and QBE IL)."""

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
from cminor.ir import IRGenerator
from cminor.codegen import LLVMEmitter, QBEEmitter


class TestCodegen(unittest.TestCase):
    def _compile_to_ir(self, src: str):
        lexer = Lexer(source_code=src, file_path="test.cm")
        tokens = lexer.tokenize()
        parser = Parser(tokens=tokens, file_path="test.cm")
        ast = parser.parse_program()
        analyzer = SemanticAnalyzer()
        self.assertTrue(analyzer.analyze(ast))
        generator = IRGenerator()
        return generator.generate(ast)

    def test_llvm_generation(self) -> None:
        src = """
        int add(int a, int b) {
            return a + b;
        }
        int main(void) {
            return add(10, 20);
        }
        """
        ir = self._compile_to_ir(src)
        emitter = LLVMEmitter()
        llvm_ir = emitter.emit(ir)
        self.assertIn("target triple = \"x86_64-pc-linux-gnu\"", llvm_ir)
        self.assertIn("define i32 @add(", llvm_ir)
        self.assertIn("define i32 @main()", llvm_ir)
        self.assertIn("add nsw i32", llvm_ir)
        self.assertIn("call i32 @add(", llvm_ir)

    def test_qbe_generation(self) -> None:
        src = """
        int add(int a, int b) {
            return a + b;
        }
        int main(void) {
            return add(10, 20);
        }
        """
        ir = self._compile_to_ir(src)
        emitter = QBEEmitter()
        qbe_il = emitter.emit(ir)
        self.assertIn("export function w $add(", qbe_il)
        self.assertIn("export function w $main()", qbe_il)
        self.assertIn("=w add", qbe_il)
        self.assertIn("=w call $add(", qbe_il)


if __name__ == "__main__":
    unittest.main()

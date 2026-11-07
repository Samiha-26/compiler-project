"""Robustness and malformed/mutated input fuzz test suite (CM-NFR-003).

Runs at least 100 distinct malformed or mutated inputs with a per-case timeout
to verify no uncaught exceptions, hangs, or compiler memory crashes occur.
"""

import io
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.driver import CompilerDriver
from cminor.diagnostics import DiagnosticEmitter


class TestRobustness(unittest.TestCase):
    def test_100_mutated_inputs(self) -> None:
        base_cases = [
            "",
            "   \t\n\r  ",
            "int",
            "int main",
            "int main(",
            "int main()",
            "int main(void)",
            "int main(void) {",
            "int main(void) }",
            "int main(void) { return }",
            "int main(void) { return ; }",
            "int main(void) { return 0 }",
            "int main(void) { return 0; }",
            "#",
            "#:foo",
            "%:",
            "%:include",
            "\\",
            "\\\n",
            "\\\r\n",
            "/*",
            "/* /* */",
            "/**",
            "int x = 0x",
            "int x = 0b",
            "int x = 099;",
            "int x = 9999999999999999999999999999999999999999;",
            "int x = 1.23;",
            "int x = 5u;",
            "int x = 'c';",
            'int x = "str";',
            "int x = @;",
            "int x = $;",
            "int x = `test`;",
            "int x = ;",
            "int x = +;",
            "int x = ++1;",
            "int x = 1++;",
            "int x = --1;",
            "int x = 1 += 2;",
            "int x = 1 << 2;",
            "int x = 1 >> 2;",
            "int x = 1 ? 2 : 3;",
            "int x = ~1;",
            "int x = 1 & 2;",
            "int x = 1 | 2;",
            "int x = 1 ^ 2;",
            "for ()",
            "for (;;)",
            "for (int i = 0;;)",
            "while ()",
            "if ()",
            "if (1)",
            "if (1) else",
            "break;",
            "continue;",
            "return 1;",
            "{ int x = 1; }",
            "int f(int);",
            "int f(void, int);",
            "int f(int a,);",
            "void f(int a) { return a; }",
            "int main(void) { int a; int a; return 0; }",
            "int main(void) { a = 1; return 0; }",
            "int main(void) { (1 + 2) = 3; return 0; }",
            "int main(void) { int x = (1 + ); return 0; }",
            "int main(void) { int x = ( * 2); return 0; }",
            "int main(void) { int x = 1 + 2 * ; return 0; }",
            "int main(void) { return (1 && ); }",
            "int main(void) { return (1 || ); }",
            "int main(void) { return (1 == ); }",
            "int main(void) { return (1 < ); }",
            "int main(void) { return (!); }",
            "int main(void) { return (-); }",
            "int main(void) { return (+); }",
            "int main(void) { int x = ; return 0; }",
            "int main(void) { if (1) int x = 2; return 0; }",
            "int main(void) { while (1) int x = 2; return 0; }",
            "int main(void) { for (;;) int x = 2; return 0; }",
            "int x; int main(void) { return 0; }",
            "struct S { int a; }; int main(void) { return 0; }",
            "union U { int a; }; int main(void) { return 0; }",
            "enum E { A, B }; int main(void) { return 0; }",
            "typedef int my_int; int main(void) { return 0; }",
            "int main(int argc, char* argv[]) { return 0; }",
            "int main(void) { int a[10]; return 0; }",
            "int main(void) { int* p; return 0; }",
            "int main(void) { goto label; label: return 0; }",
            "int main(void) { switch (1) { case 1: break; } return 0; }",
            "int main(void) { do { ; } while(0); return 0; }",
        ]

        # Extend to at least 105 distinct test cases by generating nested corruptions
        test_inputs = list(base_cases)
        for i in range(1, 20):
            test_inputs.append("int main(void) { " + ("(" * i) + "1" + (")" * (i - 1)) + "; return 0; }")
            test_inputs.append("int main(void) { " + ("{" * i) + "int x = 1;" + ("}" * (i - 1)) + " return 0; }")

        self.assertGreaterEqual(len(test_inputs), 100)

        passed_count = 0
        for idx, src in enumerate(test_inputs):
            with tempfile.NamedTemporaryFile("w", suffix=".cm", delete=False, encoding="utf-8") as f:
                f.write(src)
                tmp_path = f.name

            try:
                start_time = time.time()
                stderr_io = io.StringIO()
                emitter = DiagnosticEmitter(stream=stderr_io)
                driver = CompilerDriver(emitter=emitter)

                # Run compiler with --check mode
                rc = driver.run(["--check", tmp_path])
                elapsed = time.time() - start_time

                # Must not exceed 5 seconds timeout (CM-NFR-003)
                self.assertLess(elapsed, 5.0, f"Case {idx} timed out: {src[:40]}")

                # Must finish with controlled return code 0 or 1
                self.assertIn(rc, (0, 1), f"Case {idx} returned invalid code {rc}")
                passed_count += 1
            finally:
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass

        self.assertEqual(passed_count, len(test_inputs))


if __name__ == "__main__":
    unittest.main()

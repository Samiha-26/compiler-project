"""Unit tests for cminorcc driver and CLI flags."""

import io
import sys
import tempfile
import unittest
from pathlib import Path

# Add src/ to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cminor.driver import CompilerDriver
from cminor.diagnostics import DiagnosticEmitter


class TestDriverCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.stderr_io = io.StringIO()
        self.stdout_io = io.StringIO()
        self.emitter = DiagnosticEmitter(stream=self.stderr_io)
        self.driver = CompilerDriver(emitter=self.emitter)

    def test_version_flag(self) -> None:
        saved_stdout = sys.stdout
        sys.stdout = self.stdout_io
        try:
            rc = self.driver.run(["--version"])
            self.assertEqual(rc, 0)
            self.assertIn("cminorcc version", self.stdout_io.getvalue())
        finally:
            sys.stdout = saved_stdout

    def test_capabilities_flag(self) -> None:
        saved_stdout = sys.stdout
        sys.stdout = self.stdout_io
        try:
            rc = self.driver.run(["--capabilities"])
            self.assertEqual(rc, 0)
            output = self.stdout_io.getvalue()
            self.assertIn("C Minor Compiler", output)
            self.assertIn("Linux x86-64", output)
            self.assertIn("llvm", output)
        finally:
            sys.stdout = saved_stdout

    def test_missing_input_file_returns_2(self) -> None:
        rc = self.driver.run([])
        self.assertEqual(rc, 2)
        self.assertIn("COMMAND_ERROR", self.stderr_io.getvalue())

    def test_invalid_extension_returns_2(self) -> None:
        rc = self.driver.run(["sample.txt"])
        self.assertEqual(rc, 2)
        self.assertIn("COMMAND_ERROR", self.stderr_io.getvalue())

    def test_mutually_exclusive_flags_returns_2(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".cm") as tmp:
            rc = self.driver.run(["--check", "--dump-tokens", tmp.name])
            self.assertEqual(rc, 2)
            self.assertIn("COMMAND_ERROR", self.stderr_io.getvalue())

    def test_nonexistent_file_returns_1(self) -> None:
        rc = self.driver.run(["nonexistent_file.cm"])
        self.assertEqual(rc, 1)
        self.assertIn("IO_ERROR", self.stderr_io.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Diagnostic handling, source location tracking, and error categories."""

from __future__ import annotations
import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class DiagnosticSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


class DiagnosticCode(Enum):
    LEXICAL_ERROR = "LEXICAL_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    NAME_ERROR = "NAME_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    CALL_ERROR = "CALL_ERROR"
    RETURN_ERROR = "RETURN_ERROR"
    CONTROL_FLOW_ERROR = "CONTROL_FLOW_ERROR"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    UNSUPPORTED_PREPROCESSING_DIRECTIVE = "UNSUPPORTED_PREPROCESSING_DIRECTIVE"
    UNSUPPORTED_LINE_SPLICING = "UNSUPPORTED_LINE_SPLICING"
    IO_ERROR = "IO_ERROR"
    BACKEND_ERROR = "BACKEND_ERROR"
    COMMAND_ERROR = "COMMAND_ERROR"
    LIMIT_ERROR = "LIMIT_ERROR"


@dataclass(frozen=True)
class SourceLocation:
    """1-based source location within a file."""
    file_path: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}"


@dataclass(frozen=True)
class SourceSpan:
    """Range of source characters."""
    start: SourceLocation
    end: SourceLocation

    def __str__(self) -> str:
        return f"{self.start}"


@dataclass
class Diagnostic:
    code: DiagnosticCode
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    location: Optional[SourceLocation] = None
    related_location: Optional[SourceLocation] = None
    related_message: Optional[str] = None

    def format(self) -> str:
        loc_str = str(self.location) if self.location else "<unknown>"
        sev_str = self.severity.value
        msg = f"{loc_str}: {sev_str}: [{self.code.value}] {self.message}"
        if self.related_location and self.related_message:
            msg += f"\n{self.related_location}: note: {self.related_message}"
        return msg


class DiagnosticEmitter:
    """Collects and reports diagnostics."""

    def __init__(self, stream=None) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.diagnostics: List[Diagnostic] = []

    def report(
        self,
        code: DiagnosticCode,
        message: str,
        location: Optional[SourceLocation] = None,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
        related_location: Optional[SourceLocation] = None,
        related_message: Optional[str] = None,
    ) -> None:
        diag = Diagnostic(
            code=code,
            message=message,
            severity=severity,
            location=location,
            related_location=related_location,
            related_message=related_message,
        )
        self.diagnostics.append(diag)
        print(diag.format(), file=self.stream)

    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    def clear(self) -> None:
        self.diagnostics.clear()


class CompilerException(Exception):
    """Exception raised when compilation must halt due to an error."""

    def __init__(
        self,
        code: DiagnosticCode,
        message: str,
        location: Optional[SourceLocation] = None,
        exit_code: int = 1,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.location = location
        self.exit_code = exit_code

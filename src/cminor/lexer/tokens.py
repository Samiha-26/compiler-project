"""Token definitions and lexical structures for C Minor."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

from cminor.diagnostics import SourceLocation, SourceSpan


class TokenType(Enum):
    # End of File
    EOF = auto()

    # Literals & Identifiers
    IDENTIFIER = auto()
    INT_LITERAL = auto()

    # Keywords (CM-LEX-001)
    KW_INT = auto()
    KW_VOID = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_BREAK = auto()
    KW_CONTINUE = auto()
    KW_RETURN = auto()

    # Operators (CM-LEX-004)
    PLUS = auto()         # +
    MINUS = auto()        # -
    STAR = auto()         # *
    SLASH = auto()        # /
    PERCENT = auto()      # %

    LESS = auto()         # <
    LESS_EQUAL = auto()   # <=
    GREATER = auto()      # >
    GREATER_EQUAL = auto()# >=
    EQUAL_EQUAL = auto()  # ==
    BANG_EQUAL = auto()   # !=

    BANG = auto()         # !
    AMP_AMP = auto()      # &&
    PIPE_PIPE = auto()    # ||

    ASSIGN = auto()       # =

    # Punctuators
    LPAREN = auto()       # (
    RPAREN = auto()       # )
    LBRACE = auto()       # {
    RBRACE = auto()       # }
    SEMICOLON = auto()    # ;
    COMMA = auto()        # ,


KEYWORDS = {
    "int": TokenType.KW_INT,
    "void": TokenType.KW_VOID,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "for": TokenType.KW_FOR,
    "break": TokenType.KW_BREAK,
    "continue": TokenType.KW_CONTINUE,
    "return": TokenType.KW_RETURN,
}

# Recognized C23 keywords that are excluded from C Minor and must not be used as identifiers (CM-LEX-001)
C23_RESERVED_KEYWORDS = {
    "alignas", "alignof", "auto", "bool", "case", "char", "const", "constexpr",
    "default", "do", "double", "enum", "extern", "false", "float", "goto",
    "inline", "long", "nullptr", "register", "restrict", "short", "signed",
    "sizeof", "static", "static_assert", "struct", "switch", "thread_local",
    "true", "typedef", "typeof", "typeof_unqual", "union", "unsigned", "volatile",
    "_Alignas", "_Alignof", "_Atomic", "_BitInt", "_Bool", "_Complex",
    "_Decimal128", "_Decimal32", "_Decimal64", "_Generic", "_Imaginary",
    "_Noreturn", "_Static_assert", "_Thread_local",
}


@dataclass(frozen=True)
class Token:
    """Represents a scanned lexical token."""
    type: TokenType
    lexeme: str
    span: SourceSpan
    value: Optional[Any] = None

    @property
    def location(self) -> SourceLocation:
        return self.span.start

    def __str__(self) -> str:
        loc = f"{self.span.start.line}:{self.span.start.column}"
        if self.value is not None and self.type == TokenType.INT_LITERAL:
            return f"[{loc}] {self.type.name}('{self.lexeme}', value={self.value})"
        return f"[{loc}] {self.type.name}('{self.lexeme}')"

"""Handwritten scanner for C Minor complying with Sections 4 & Appendix A."""

from __future__ import annotations
import sys
from typing import List, Optional, Tuple

from cminor.diagnostics import (
    DiagnosticCode,
    DiagnosticEmitter,
    SourceLocation,
    SourceSpan,
)
from cminor.lexer.tokens import (
    Token,
    TokenType,
    KEYWORDS,
    C23_RESERVED_KEYWORDS,
)

MAX_INT = 2147483647


class Lexer:
    """Scans C Minor source code into tokens."""

    def __init__(
        self,
        source_code: str,
        file_path: str = "<stdin>",
        emitter: Optional[DiagnosticEmitter] = None,
    ) -> None:
        self.source = source_code
        self.file_path = file_path
        self.emitter = emitter or DiagnosticEmitter(sys.stderr)
        self.length = len(source_code)
        self.pos = 0
        self.line = 1
        self.column = 1
        self.at_line_start = True

    def _curr_loc(self) -> SourceLocation:
        return SourceLocation(self.file_path, self.line, self.column)

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return ""

    def _advance(self) -> str:
        if self.pos >= self.length:
            return ""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
            self.at_line_start = True
        else:
            self.column += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self.source.startswith(expected, self.pos):
            for _ in expected:
                self._advance()
            return True
        return False

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            start_pos = self.pos
            start_loc = self._curr_loc()
            ch = self._peek()

            # 1. Whitespace handling (CM-LEX-003)
            # Space, horizontal tab, vertical tab, form feed, CR, LF
            if ch in " \t\v\f\r\n":
                if ch == "\r" and self._peek(1) == "\n":
                    self._advance()  # consume \r
                    self._advance()  # consume \n
                else:
                    self._advance()
                continue

            # 2. Line Splicing check (CM-LEX-006)
            if ch == "\\":
                if self._peek(1) == "\n" or (self._peek(1) == "\r" and self._peek(2) == "\n"):
                    self._advance()  # consume \
                    if self._peek() == "\r":
                        self._advance()
                    self._advance()  # consume \n
                    end_loc = self._curr_loc()
                    self.emitter.report(
                        code=DiagnosticCode.UNSUPPORTED_LINE_SPLICING,
                        message="Source line splicing with backslash-newline is not supported.",
                        location=start_loc,
                    )
                    continue
                else:
                    self._advance()
                    self.emitter.report(
                        code=DiagnosticCode.LEXICAL_ERROR,
                        message="Unexpected character '\\'.",
                        location=start_loc,
                    )
                    self.at_line_start = False
                    continue

            # 3. Comments (CM-LEX-003)
            if ch == "/" and self._peek(1) == "/":
                # Line comment: consume through line end / EOF
                self._advance()  # consume /
                self._advance()  # consume /
                while self.pos < self.length and self._peek() not in "\r\n":
                    self._advance()
                # Do NOT change self.at_line_start! (CM-LEX-005)
                continue

            if ch == "/" and self._peek(1) == "*":
                # Block comment
                self._advance()  # consume /
                self._advance()  # consume *
                terminated = False
                while self.pos < self.length:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()  # *
                        self._advance()  # /
                        terminated = True
                        break
                    if self._peek() == "\r" and self._peek(1) == "\n":
                        self._advance()
                        self._advance()
                    else:
                        self._advance()

                if not terminated:
                    self.emitter.report(
                        code=DiagnosticCode.LEXICAL_ERROR,
                        message="Unterminated block comment /* ... */.",
                        location=start_loc,
                    )
                # Comments preserve token boundaries and do NOT reset at_line_start
                continue

            # 4. Preprocessing Directive check (CM-LEX-005)
            # '#', or '%:' digraph
            if ch == "#" or (ch == "%" and self._peek(1) == ":"):
                is_digraph = ch == "%"
                if is_digraph:
                    self._advance()  # %
                    self._advance()  # :
                    lexeme = "%:"
                else:
                    self._advance()  # #
                    lexeme = "#"

                if self.at_line_start:
                    self.emitter.report(
                        code=DiagnosticCode.UNSUPPORTED_PREPROCESSING_DIRECTIVE,
                        message=f"Preprocessing directive '{lexeme}' is not supported.",
                        location=start_loc,
                    )
                else:
                    self.emitter.report(
                        code=DiagnosticCode.LEXICAL_ERROR,
                        message=f"Unexpected '{lexeme}' outside preprocessing-directive position.",
                        location=start_loc,
                    )
                # Consume the rest of the directive line to avoid cascaded noise
                while self.pos < self.length and self._peek() not in "\r\n":
                    self._advance()
                continue

            # Non-whitespace, non-comment item encountered: line start is no longer true
            self.at_line_start = False

            # 5. Non-ASCII check (CM-LEX-006)
            if ord(ch) > 127:
                self._advance()
                self.emitter.report(
                    code=DiagnosticCode.LEXICAL_ERROR,
                    message=f"Unsupported non-ASCII character '{ch}' (code {ord(ch)}).",
                    location=start_loc,
                )
                continue

            # 6. String / Character literals check (CM-LEX-007, excluded from baseline)
            if ch in ("'", '"'):
                quote = ch
                self._advance()
                content = []
                while self.pos < self.length and self._peek() != quote and self._peek() not in "\r\n":
                    content.append(self._advance())
                if self._peek() == quote:
                    self._advance()
                    self.emitter.report(
                        code=DiagnosticCode.UNSUPPORTED_FEATURE,
                        message=f"{'Character' if quote == chr(39) else 'String'} literals are not supported in C Minor.",
                        location=start_loc,
                    )
                else:
                    self.emitter.report(
                        code=DiagnosticCode.LEXICAL_ERROR,
                        message=f"Unterminated {'character' if quote == chr(39) else 'string'} literal.",
                        location=start_loc,
                    )
                continue

            # 7. Numbers / Integer literals (CM-LEX-002)
            if ch.isdigit():
                token = self._scan_number(start_loc)
                if token:
                    tokens.append(token)
                continue

            # 8. Identifiers and Keywords (CM-LEX-001)
            if ch.isalpha() or ch == "_":
                token = self._scan_identifier(start_loc)
                if token:
                    tokens.append(token)
                continue

            # 9. Multi-character unsupported operators check (CM-LEX-004)
            unsupported_op = self._check_unsupported_operators()
            if unsupported_op:
                for _ in unsupported_op:
                    self._advance()
                self.emitter.report(
                    code=DiagnosticCode.UNSUPPORTED_FEATURE,
                    message=f"Unsupported operator '{unsupported_op}'.",
                    location=start_loc,
                )
                continue

            # 10. Valid Operators & Punctuators (CM-LEX-004)
            token = self._scan_operator_or_punctuator(start_loc)
            if token:
                tokens.append(token)
                continue

            # 11. Unknown character (CM-LEX-007)
            bad_ch = self._advance()
            self.emitter.report(
                code=DiagnosticCode.LEXICAL_ERROR,
                message=f"Unknown character '{bad_ch}'.",
                location=start_loc,
            )

        eof_loc = self._curr_loc()
        tokens.append(
            Token(
                type=TokenType.EOF,
                lexeme="",
                span=SourceSpan(eof_loc, eof_loc),
            )
        )
        return tokens

    def _scan_number(self, start_loc: SourceLocation) -> Optional[Token]:
        start_pos = self.pos
        first_ch = self._peek()

        # Check for hex (0x...) or binary (0b...)
        if first_ch == "0" and self._peek(1) in "xXbB":
            prefix = self._advance() + self._advance()
            while self._peek().isalnum():
                self._advance()
            lexeme = self.source[start_pos:self.pos]
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"Malformed or unsupported integer literal '{lexeme}'. Only decimal integer literals are supported.",
                location=start_loc,
            )
            return None

        # Check for leading zero octal or multiple zeros (e.g. 00, 012)
        if first_ch == "0" and self._peek(1).isdigit():
            while self._peek().isdigit():
                self._advance()
            # If followed by floating point or suffixes, consume as well
            if self._peek() == ".":
                self._advance()
                while self._peek().isdigit():
                    self._advance()
            while self._peek().isalpha():
                self._advance()
            lexeme = self.source[start_pos:self.pos]
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"Leading-zero octal or malformed literal '{lexeme}' is not supported.",
                location=start_loc,
            )
            return None

        # Standard decimal digits
        while self._peek().isdigit():
            self._advance()

        # Check for floating point (e.g. 1.0)
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()  # .
            while self._peek().isdigit():
                self._advance()
            while self._peek().isalpha():
                self._advance()
            lexeme = self.source[start_pos:self.pos]
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"Floating-point literal '{lexeme}' is not supported.",
                location=start_loc,
            )
            return None

        # Check for suffixes (e.g. 4u, 10L)
        if self._peek().isalpha():
            while self._peek().isalpha():
                self._advance()
            lexeme = self.source[start_pos:self.pos]
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"Integer literal suffix in '{lexeme}' is not supported.",
                location=start_loc,
            )
            return None

        lexeme = self.source[start_pos:self.pos]
        val = int(lexeme)
        if val > MAX_INT:
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"Integer literal '{lexeme}' exceeds maximum 32-bit signed int ({MAX_INT}).",
                location=start_loc,
            )
            return None

        end_loc = self._curr_loc()
        return Token(
            type=TokenType.INT_LITERAL,
            lexeme=lexeme,
            span=SourceSpan(start_loc, end_loc),
            value=val,
        )

    def _scan_identifier(self, start_loc: SourceLocation) -> Optional[Token]:
        start_pos = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        lexeme = self.source[start_pos:self.pos]
        end_loc = self._curr_loc()
        span = SourceSpan(start_loc, end_loc)

        if lexeme in KEYWORDS:
            return Token(type=KEYWORDS[lexeme], lexeme=lexeme, span=span)

        if lexeme in C23_RESERVED_KEYWORDS:
            self.emitter.report(
                code=DiagnosticCode.UNSUPPORTED_FEATURE,
                message=f"C23 keyword '{lexeme}' is reserved and not supported in C Minor.",
                location=start_loc,
            )
            return None

        return Token(type=TokenType.IDENTIFIER, lexeme=lexeme, span=span)

    def _check_unsupported_operators(self) -> Optional[str]:
        # Multi-char and single-char operators not in C Minor:
        # ++, --, +=, -=, *=, /=, %=, <<=, >>=, <<, >>, ->, &=, |=, ^=, &&=, ||=,
        # &, |, ^, ~, ?, :, ., [ , ]
        candidates = [
            "<<=", ">>=",
            "++", "--", "+=", "-=", "*=", "/=", "%=", "<<", ">>", "->",
            "&=", "|=", "^=",
            "?", "~", "^", ".", "[", "]"
        ]
        for cand in candidates:
            if self.source.startswith(cand, self.pos):
                return cand

        # Check single & or | not followed by & or |
        if self._peek() == "&" and self._peek(1) != "&":
            return "&"
        if self._peek() == "|" and self._peek(1) != "|":
            return "|"

        return None

    def _scan_operator_or_punctuator(self, start_loc: SourceLocation) -> Optional[Token]:
        start_pos = self.pos

        # Two-character operators
        two_char_map = {
            "<=": TokenType.LESS_EQUAL,
            ">=": TokenType.GREATER_EQUAL,
            "==": TokenType.EQUAL_EQUAL,
            "!=": TokenType.BANG_EQUAL,
            "&&": TokenType.AMP_AMP,
            "||": TokenType.PIPE_PIPE,
        }
        two = self._peek() + self._peek(1)
        if two in two_char_map:
            self._advance()
            self._advance()
            return Token(
                type=two_char_map[two],
                lexeme=two,
                span=SourceSpan(start_loc, self._curr_loc()),
            )

        # Single-character operators & punctuators
        single_char_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "<": TokenType.LESS,
            ">": TokenType.GREATER,
            "!": TokenType.BANG,
            "=": TokenType.ASSIGN,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA,
        }
        ch = self._peek()
        if ch in single_char_map:
            self._advance()
            return Token(
                type=single_char_map[ch],
                lexeme=ch,
                span=SourceSpan(start_loc, self._curr_loc()),
            )

        return None

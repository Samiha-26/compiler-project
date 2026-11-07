"""Recursive descent parser for C Minor complying with Appendix A."""

from __future__ import annotations
import sys
from typing import List, Optional

from cminor.diagnostics import (
    DiagnosticCode,
    DiagnosticEmitter,
    SourceLocation,
    SourceSpan,
)
from cminor.lexer.tokens import Token, TokenType
from cminor.parser.ast import (
    ASTNode,
    Program,
    FunctionDecl,
    FunctionDef,
    ParamDecl,
    VarDecl,
    TypeNode,
    BlockStmt,
    BlockItem,
    Statement,
    ExprStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    ForInit,
    BreakStmt,
    ContinueStmt,
    ReturnStmt,
    Expr,
    IntLiteralExpr,
    VarExpr,
    CallExpr,
    UnaryExpr,
    BinaryExpr,
    AssignExpr,
)


class ParseError(Exception):
    pass


class Parser:
    """Parses a token sequence into a C Minor AST."""

    def __init__(
        self,
        tokens: List[Token],
        file_path: str = "<stdin>",
        emitter: Optional[DiagnosticEmitter] = None,
    ) -> None:
        self.tokens = tokens
        self.file_path = file_path
        self.emitter = emitter or DiagnosticEmitter(sys.stderr)
        self.pos = 0

    def _curr(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def _peek_type(self, offset: int = 0) -> TokenType:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx].type
        return TokenType.EOF

    def _advance(self) -> Token:
        tok = self._curr()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    def _check(self, token_type: TokenType) -> bool:
        return self._curr().type == token_type

    def _match(self, token_type: TokenType) -> bool:
        if self._check(token_type):
            self._advance()
            return True
        return False

    def _expect(self, token_type: TokenType, msg: str) -> Token:
        if self._check(token_type):
            return self._advance()
        tok = self._curr()
        self.emitter.report(
            code=DiagnosticCode.SYNTAX_ERROR,
            message=f"{msg} (got '{tok.lexeme or tok.type.name}').",
            location=tok.location,
        )
        raise ParseError()

    def _span_from(self, start_tok: Token, end_tok: Optional[Token] = None) -> SourceSpan:
        end = end_tok if end_tok is not None else self._curr()
        return SourceSpan(start_tok.span.start, end.span.end)

    # -------------------------------------------------------------
    # Program & External Declarations
    # -------------------------------------------------------------
    def parse_program(self) -> Program:
        start_tok = self._curr()
        externals = []

        while not self._check(TokenType.EOF):
            try:
                ext = self._parse_external()
                if ext:
                    externals.append(ext)
            except ParseError:
                self._synchronize_external()

        end_tok = self._curr()
        return Program(span=self._span_from(start_tok, end_tok), externals=externals)

    def _synchronize_external(self) -> None:
        while not self._check(TokenType.EOF):
            tok = self._curr()
            if tok.type in (TokenType.KW_INT, TokenType.KW_VOID):
                return
            if tok.type == TokenType.SEMICOLON:
                self._advance()
                return
            if tok.type == TokenType.RBRACE:
                self._advance()
                return
            self._advance()

    def _parse_external(self) -> Optional[ASTNode]:
        start_tok = self._curr()
        if not (self._check(TokenType.KW_INT) or self._check(TokenType.KW_VOID)):
            self.emitter.report(
                code=DiagnosticCode.SYNTAX_ERROR,
                message=f"Expected function declaration or definition starting with 'int' or 'void'.",
                location=start_tok.location,
            )
            self._advance()
            raise ParseError()

        ret_tok = self._advance()
        ret_type = TypeNode(span=ret_tok.span, name=ret_tok.lexeme)

        name_tok = self._expect(TokenType.IDENTIFIER, "Expected function name")
        fn_name = name_tok.lexeme

        self._expect(TokenType.LPAREN, "Expected '(' after function name")

        # Parse parameter list
        # prototype_params = "void" | prototype_param { "," prototype_param } ;
        # definition_params = "void" | definition_param { "," definition_param } ;
        params: List[ParamDecl] = []
        is_void_param = False

        if self._check(TokenType.KW_VOID):
            void_tok = self._advance()
            if self._check(TokenType.RPAREN):
                is_void_param = True
            else:
                self.emitter.report(
                    code=DiagnosticCode.SYNTAX_ERROR,
                    message="'void' must be the sole parameter marker '(void)'.",
                    location=void_tok.location,
                )
                raise ParseError()
        elif not self._check(TokenType.RPAREN):
            # Parse first param
            params.append(self._parse_param())
            while self._match(TokenType.COMMA):
                params.append(self._parse_param())

        rparen_tok = self._expect(TokenType.RPAREN, "Expected ')' after parameters")

        # Now distinguish function_decl ';' vs function_def '{'
        if self._match(TokenType.SEMICOLON):
            # Function declaration (prototype)
            return FunctionDecl(
                span=self._span_from(start_tok, self._curr()),
                return_type=ret_type,
                name=fn_name,
                params=params,
            )
        elif self._check(TokenType.LBRACE):
            # Function definition
            # Verify each parameter has a name (CM-SYN-001 / Appendix A)
            for p in params:
                if not p.name:
                    self.emitter.report(
                        code=DiagnosticCode.SYNTAX_ERROR,
                        message=f"Parameter in function definition '{fn_name}' must have a name.",
                        location=p.span.start,
                    )
                    raise ParseError()
            body = self._parse_block()
            return FunctionDef(
                span=self._span_from(start_tok, self._curr()),
                return_type=ret_type,
                name=fn_name,
                params=params,
                body=body,
            )
        else:
            tok = self._curr()
            self.emitter.report(
                code=DiagnosticCode.SYNTAX_ERROR,
                message=f"Expected ';' or '{{' after function header, got '{tok.lexeme}'.",
                location=tok.location,
            )
            raise ParseError()

    def _parse_param(self) -> ParamDecl:
        start_tok = self._curr()
        type_tok = self._expect(TokenType.KW_INT, "Parameter type must be 'int'")
        type_node = TypeNode(span=type_tok.span, name="int")

        name = None
        end_tok = type_tok
        if self._check(TokenType.IDENTIFIER):
            id_tok = self._advance()
            name = id_tok.lexeme
            end_tok = id_tok

        return ParamDecl(span=self._span_from(start_tok, end_tok), type_node=type_node, name=name)

    # -------------------------------------------------------------
    # Declarations and Statements
    # -------------------------------------------------------------
    def _parse_block(self) -> BlockStmt:
        start_tok = self._expect(TokenType.LBRACE, "Expected '{' to start block")
        items: List[BlockItem] = []

        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            try:
                item = self._parse_block_item()
                if item:
                    items.append(item)
            except ParseError:
                self._synchronize_stmt()

        end_tok = self._expect(TokenType.RBRACE, "Expected '}' to close block")
        return BlockStmt(span=self._span_from(start_tok, end_tok), items=items)

    def _synchronize_stmt(self) -> None:
        while not self._check(TokenType.EOF):
            tok = self._curr()
            if tok.type == TokenType.SEMICOLON:
                self._advance()
                return
            if tok.type in (
                TokenType.RBRACE,
                TokenType.KW_IF,
                TokenType.KW_WHILE,
                TokenType.KW_FOR,
                TokenType.KW_RETURN,
                TokenType.KW_BREAK,
                TokenType.KW_CONTINUE,
                TokenType.KW_INT,
            ):
                return
            self._advance()

    def _parse_block_item(self) -> Optional[BlockItem]:
        # block_item = local_decl | statement ;
        if self._check(TokenType.KW_INT):
            return self._parse_local_decl()
        return self._parse_statement()

    def _parse_local_decl(self) -> VarDecl:
        # local_decl = "int" identifier [ "=" assignment_expr ] ";" ;
        start_tok = self._expect(TokenType.KW_INT, "Expected 'int'")
        type_node = TypeNode(span=start_tok.span, name="int")

        name_tok = self._expect(TokenType.IDENTIFIER, "Expected variable name")
        name = name_tok.lexeme

        init_expr = None
        if self._match(TokenType.ASSIGN):
            init_expr = self._parse_assignment_expr()

        end_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDecl(
            span=self._span_from(start_tok, end_tok),
            type_node=type_node,
            name=name,
            init=init_expr,
        )

    def _parse_statement(self) -> Statement:
        tok = self._curr()

        # Reject bare unbraced declarations where a statement is expected (CM-SYN-004)
        if tok.type == TokenType.KW_INT:
            self.emitter.report(
                code=DiagnosticCode.SYNTAX_ERROR,
                message="A declaration cannot appear as a bare statement. Use a block '{ ... }'.",
                location=tok.location,
            )
            raise ParseError()

        if tok.type == TokenType.LBRACE:
            return self._parse_block()
        elif tok.type == TokenType.KW_IF:
            return self._parse_if_stmt()
        elif tok.type == TokenType.KW_WHILE:
            return self._parse_while_stmt()
        elif tok.type == TokenType.KW_FOR:
            return self._parse_for_stmt()
        elif tok.type == TokenType.KW_BREAK:
            return self._parse_break_stmt()
        elif tok.type == TokenType.KW_CONTINUE:
            return self._parse_continue_stmt()
        elif tok.type == TokenType.KW_RETURN:
            return self._parse_return_stmt()
        else:
            return self._parse_expr_stmt()

    def _parse_expr_stmt(self) -> ExprStmt:
        start_tok = self._curr()
        if self._match(TokenType.SEMICOLON):
            return ExprStmt(span=self._span_from(start_tok, start_tok), expr=None)

        expr = self._parse_assignment_expr()
        end_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after expression statement")
        return ExprStmt(span=self._span_from(start_tok, end_tok), expr=expr)

    def _parse_if_stmt(self) -> IfStmt:
        start_tok = self._advance()  # consume 'if'
        self._expect(TokenType.LPAREN, "Expected '(' after 'if'")
        cond = self._parse_assignment_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after if-condition")

        then_branch = self._parse_statement()

        else_branch = None
        if self._match(TokenType.KW_ELSE):
            else_branch = self._parse_statement()

        return IfStmt(
            span=self._span_from(start_tok, self._curr()),
            cond=cond,
            then_branch=then_branch,
            else_branch=else_branch,
        )

    def _parse_while_stmt(self) -> WhileStmt:
        start_tok = self._advance()  # consume 'while'
        self._expect(TokenType.LPAREN, "Expected '(' after 'while'")
        cond = self._parse_assignment_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after while-condition")

        body = self._parse_statement()
        return WhileStmt(
            span=self._span_from(start_tok, self._curr()),
            cond=cond,
            body=body,
        )

    def _parse_for_stmt(self) -> ForStmt:
        start_tok = self._advance()  # consume 'for'
        self._expect(TokenType.LPAREN, "Expected '(' after 'for'")

        # for_init = local_decl | [ assignment_expr ] ";" ;
        init: Optional[ForInit] = None
        if self._check(TokenType.KW_INT):
            init = self._parse_local_decl()
        elif self._match(TokenType.SEMICOLON):
            init = None
        else:
            init_expr = self._parse_assignment_expr()
            semi_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after for-initializer")
            init = ExprStmt(span=self._span_from(start_tok, semi_tok), expr=init_expr)

        # condition: [ assignment_expr ] ";"
        cond: Optional[Expr] = None
        if not self._check(TokenType.SEMICOLON):
            cond = self._parse_assignment_expr()
        self._expect(TokenType.SEMICOLON, "Expected ';' after for-condition")

        # update: [ assignment_expr ] ")"
        step: Optional[Expr] = None
        if not self._check(TokenType.RPAREN):
            step = self._parse_assignment_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after for-update")

        body = self._parse_statement()
        return ForStmt(
            span=self._span_from(start_tok, self._curr()),
            init=init,
            cond=cond,
            step=step,
            body=body,
        )

    def _parse_break_stmt(self) -> BreakStmt:
        start_tok = self._advance()  # consume 'break'
        end_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after 'break'")
        return BreakStmt(span=self._span_from(start_tok, end_tok))

    def _parse_continue_stmt(self) -> ContinueStmt:
        start_tok = self._advance()  # consume 'continue'
        end_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after 'continue'")
        return ContinueStmt(span=self._span_from(start_tok, end_tok))

    def _parse_return_stmt(self) -> ReturnStmt:
        start_tok = self._advance()  # consume 'return'
        if self._match(TokenType.SEMICOLON):
            return ReturnStmt(span=self._span_from(start_tok, start_tok), expr=None)

        expr = self._parse_assignment_expr()
        end_tok = self._expect(TokenType.SEMICOLON, "Expected ';' after return expression")
        return ReturnStmt(span=self._span_from(start_tok, end_tok), expr=expr)

    # -------------------------------------------------------------
    # Expressions (Precedence hierarchy Appendix A.2)
    # -------------------------------------------------------------
    def _parse_assignment_expr(self) -> Expr:
        # assignment_expr = logical_or [ "=" assignment_expr ] ;
        lhs = self._parse_logical_or()

        if self._match(TokenType.ASSIGN):
            rhs = self._parse_assignment_expr()
            return AssignExpr(
                span=SourceSpan(lhs.span.start, rhs.span.end),
                target=lhs,
                value=rhs,
            )

        return lhs

    def _parse_logical_or(self) -> Expr:
        # logical_or = logical_and { "||" logical_and } ;
        expr = self._parse_logical_and()
        while self._match(TokenType.PIPE_PIPE):
            op_tok = self.tokens[self.pos - 1]
            right = self._parse_logical_and()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op="||",
                left=expr,
                right=right,
            )
        return expr

    def _parse_logical_and(self) -> Expr:
        # logical_and = equality { "&&" equality } ;
        expr = self._parse_equality()
        while self._match(TokenType.AMP_AMP):
            op_tok = self.tokens[self.pos - 1]
            right = self._parse_equality()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op="&&",
                left=expr,
                right=right,
            )
        return expr

    def _parse_equality(self) -> Expr:
        # equality = relational { ( "==" | "!=" ) relational } ;
        expr = self._parse_relational()
        while self._check(TokenType.EQUAL_EQUAL) or self._check(TokenType.BANG_EQUAL):
            op_tok = self._advance()
            right = self._parse_relational()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op=op_tok.lexeme,
                left=expr,
                right=right,
            )
        return expr

    def _parse_relational(self) -> Expr:
        # relational = additive { ( "<" | "<=" | ">" | ">=" ) additive } ;
        expr = self._parse_additive()
        while self._check(TokenType.LESS) or self._check(TokenType.LESS_EQUAL) or \
              self._check(TokenType.GREATER) or self._check(TokenType.GREATER_EQUAL):
            op_tok = self._advance()
            right = self._parse_additive()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op=op_tok.lexeme,
                left=expr,
                right=right,
            )
        return expr

    def _parse_additive(self) -> Expr:
        # additive = multiplicative { ( "+" | "-" ) multiplicative } ;
        expr = self._parse_multiplicative()
        while self._check(TokenType.PLUS) or self._check(TokenType.MINUS):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op=op_tok.lexeme,
                left=expr,
                right=right,
            )
        return expr

    def _parse_multiplicative(self) -> Expr:
        # multiplicative = unary { ( "*" | "/" | "%" ) unary } ;
        expr = self._parse_unary()
        while self._check(TokenType.STAR) or self._check(TokenType.SLASH) or self._check(TokenType.PERCENT):
            op_tok = self._advance()
            right = self._parse_unary()
            expr = BinaryExpr(
                span=SourceSpan(expr.span.start, right.span.end),
                op=op_tok.lexeme,
                left=expr,
                right=right,
            )
        return expr

    def _parse_unary(self) -> Expr:
        # unary = ( "+" | "-" | "!" ) unary | primary ;
        if self._check(TokenType.PLUS) or self._check(TokenType.MINUS) or self._check(TokenType.BANG):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryExpr(
                span=SourceSpan(op_tok.span.start, operand.span.end),
                op=op_tok.lexeme,
                operand=operand,
            )
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        # primary = integer_literal
        #         | identifier [ "(" [ arg_list ] ")" ]
        #         | "(" assignment_expr ")" ;
        tok = self._curr()

        if tok.type == TokenType.INT_LITERAL:
            self._advance()
            return IntLiteralExpr(
                span=tok.span,
                value=tok.value if tok.value is not None else int(tok.lexeme),
            )

        if tok.type == TokenType.IDENTIFIER:
            id_tok = self._advance()
            if self._match(TokenType.LPAREN):
                # Function call
                args: List[Expr] = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._parse_assignment_expr())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_assignment_expr())
                rparen_tok = self._expect(TokenType.RPAREN, "Expected ')' after function call arguments")
                return CallExpr(
                    span=SourceSpan(id_tok.span.start, rparen_tok.span.end),
                    callee=id_tok.lexeme,
                    args=args,
                )
            else:
                return VarExpr(span=id_tok.span, name=id_tok.lexeme)

        if self._match(TokenType.LPAREN):
            start_tok = tok
            expr = self._parse_assignment_expr()
            rparen_tok = self._expect(TokenType.RPAREN, "Expected ')' matching '('")
            # Preserve parenthesized span
            expr.span = SourceSpan(start_tok.span.start, rparen_tok.span.end)
            return expr

        self.emitter.report(
            code=DiagnosticCode.SYNTAX_ERROR,
            message=f"Expected expression, got '{tok.lexeme or tok.type.name}'.",
            location=tok.location,
        )
        raise ParseError()

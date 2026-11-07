"""Abstract Syntax Tree (AST) node definitions for C Minor."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union

from cminor.diagnostics import SourceSpan


@dataclass
class ASTNode:
    span: SourceSpan


# Types
@dataclass
class TypeNode(ASTNode):
    name: str  # "int" or "void"


# Declarations & Parameters
@dataclass
class ParamDecl(ASTNode):
    type_node: TypeNode
    name: Optional[str] = None


@dataclass
class VarDecl(ASTNode):
    type_node: TypeNode
    name: str
    init: Optional[Expr] = None


@dataclass
class FunctionDecl(ASTNode):
    return_type: TypeNode
    name: str
    params: List[ParamDecl]


@dataclass
class FunctionDef(ASTNode):
    return_type: TypeNode
    name: str
    params: List[ParamDecl]
    body: BlockStmt


# Expressions
@dataclass
class Expr(ASTNode):
    # Inferred during semantic analysis
    inferred_type: Optional[str] = None  # "int" or "void"
    is_lvalue: bool = False


@dataclass
class IntLiteralExpr(Expr):
    value: int = 0


@dataclass
class VarExpr(Expr):
    name: str = ""


@dataclass
class CallExpr(Expr):
    callee: str = ""
    args: List[Expr] = None  # type: ignore

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class UnaryExpr(Expr):
    op: str = ""  # "+", "-", "!"
    operand: Expr = None  # type: ignore


@dataclass
class BinaryExpr(Expr):
    op: str = ""  # "+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=", "&&", "||"
    left: Expr = None  # type: ignore
    right: Expr = None  # type: ignore


@dataclass
class AssignExpr(Expr):
    target: Expr = None  # type: ignore
    value: Expr = None  # type: ignore


# Statements
@dataclass
class Statement(ASTNode):
    pass


@dataclass
class ExprStmt(Statement):
    expr: Optional[Expr] = None


ForInit = Union[VarDecl, ExprStmt]


@dataclass
class BlockStmt(Statement):
    items: List[BlockItem] = None  # type: ignore

    def __post_init__(self):
        if self.items is None:
            self.items = []


BlockItem = Union[VarDecl, Statement]


@dataclass
class IfStmt(Statement):
    cond: Expr = None  # type: ignore
    then_branch: Statement = None  # type: ignore
    else_branch: Optional[Statement] = None


@dataclass
class WhileStmt(Statement):
    cond: Expr = None  # type: ignore
    body: Statement = None  # type: ignore


@dataclass
class ForStmt(Statement):
    init: Optional[ForInit] = None
    cond: Optional[Expr] = None
    step: Optional[Expr] = None
    body: Statement = None  # type: ignore


@dataclass
class BreakStmt(Statement):
    pass


@dataclass
class ContinueStmt(Statement):
    pass


@dataclass
class ReturnStmt(Statement):
    expr: Optional[Expr] = None


# Program root
@dataclass
class Program(ASTNode):
    externals: List[Union[FunctionDecl, FunctionDef]] = None  # type: ignore

    def __post_init__(self):
        if self.externals is None:
            self.externals = []

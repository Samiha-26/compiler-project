"""Inspectable, deterministic AST dump formatting for C Minor."""

from __future__ import annotations
from typing import List
from cminor.parser.ast import (
    ASTNode,
    Program,
    FunctionDecl,
    FunctionDef,
    ParamDecl,
    VarDecl,
    BlockStmt,
    ExprStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    BreakStmt,
    ContinueStmt,
    ReturnStmt,
    IntLiteralExpr,
    VarExpr,
    CallExpr,
    UnaryExpr,
    BinaryExpr,
    AssignExpr,
)


class ASTDumper:
    """Formats an AST into a human-readable, deterministic indented text representation."""

    def __init__(self) -> None:
        self.lines: List[str] = []

    def dump(self, node: ASTNode) -> str:
        self.lines.clear()
        self._visit(node, indent=0)
        return "\n".join(self.lines)

    def _visit(self, node: ASTNode, indent: int) -> None:
        prefix = "  " * indent
        loc = f"<{node.span.start.line}:{node.span.start.column}>"

        if isinstance(node, Program):
            self.lines.append(f"{prefix}Program {loc}")
            for ext in node.externals:
                self._visit(ext, indent + 1)

        elif isinstance(node, FunctionDecl):
            param_str = ", ".join(f"{p.type_node.name}" + (f" {p.name}" if p.name else "") for p in node.params)
            self.lines.append(f"{prefix}FunctionDecl {loc}: {node.return_type.name} {node.name}({param_str or 'void'});")

        elif isinstance(node, FunctionDef):
            param_str = ", ".join(f"{p.type_node.name} {p.name}" for p in node.params)
            self.lines.append(f"{prefix}FunctionDef {loc}: {node.return_type.name} {node.name}({param_str or 'void'})")
            self._visit(node.body, indent + 1)

        elif isinstance(node, VarDecl):
            if node.init:
                self.lines.append(f"{prefix}VarDecl {loc}: {node.type_node.name} {node.name} =")
                self._visit(node.init, indent + 1)
            else:
                self.lines.append(f"{prefix}VarDecl {loc}: {node.type_node.name} {node.name}")

        elif isinstance(node, BlockStmt):
            self.lines.append(f"{prefix}Block {loc}")
            for item in node.items:
                self._visit(item, indent + 1)

        elif isinstance(node, ExprStmt):
            if node.expr:
                self.lines.append(f"{prefix}ExprStmt {loc}")
                self._visit(node.expr, indent + 1)
            else:
                self.lines.append(f"{prefix}EmptyStmt {loc} ;")

        elif isinstance(node, IfStmt):
            self.lines.append(f"{prefix}IfStmt {loc}")
            self.lines.append(f"{prefix}  Condition:")
            self._visit(node.cond, indent + 2)
            self.lines.append(f"{prefix}  Then:")
            self._visit(node.then_branch, indent + 2)
            if node.else_branch:
                self.lines.append(f"{prefix}  Else:")
                self._visit(node.else_branch, indent + 2)

        elif isinstance(node, WhileStmt):
            self.lines.append(f"{prefix}WhileStmt {loc}")
            self.lines.append(f"{prefix}  Condition:")
            self._visit(node.cond, indent + 2)
            self.lines.append(f"{prefix}  Body:")
            self._visit(node.body, indent + 2)

        elif isinstance(node, ForStmt):
            self.lines.append(f"{prefix}ForStmt {loc}")
            self.lines.append(f"{prefix}  Init:")
            if node.init:
                self._visit(node.init, indent + 2)
            else:
                self.lines.append(f"{prefix}    <none>")
            self.lines.append(f"{prefix}  Condition:")
            if node.cond:
                self._visit(node.cond, indent + 2)
            else:
                self.lines.append(f"{prefix}    <none>")
            self.lines.append(f"{prefix}  Update:")
            if node.step:
                self._visit(node.step, indent + 2)
            else:
                self.lines.append(f"{prefix}    <none>")
            self.lines.append(f"{prefix}  Body:")
            self._visit(node.body, indent + 2)

        elif isinstance(node, BreakStmt):
            self.lines.append(f"{prefix}BreakStmt {loc}")

        elif isinstance(node, ContinueStmt):
            self.lines.append(f"{prefix}ContinueStmt {loc}")

        elif isinstance(node, ReturnStmt):
            if node.expr:
                self.lines.append(f"{prefix}ReturnStmt {loc}")
                self._visit(node.expr, indent + 1)
            else:
                self.lines.append(f"{prefix}ReturnStmt {loc} <void>")

        elif isinstance(node, AssignExpr):
            self.lines.append(f"{prefix}AssignExpr {loc} (=)")
            self._visit(node.target, indent + 1)
            self._visit(node.value, indent + 1)

        elif isinstance(node, BinaryExpr):
            self.lines.append(f"{prefix}BinaryExpr {loc} ({node.op})")
            self._visit(node.left, indent + 1)
            self._visit(node.right, indent + 1)

        elif isinstance(node, UnaryExpr):
            self.lines.append(f"{prefix}UnaryExpr {loc} ({node.op})")
            self._visit(node.operand, indent + 1)

        elif isinstance(node, CallExpr):
            self.lines.append(f"{prefix}CallExpr {loc}: {node.callee}()")
            for arg in node.args:
                self._visit(arg, indent + 1)

        elif isinstance(node, VarExpr):
            self.lines.append(f"{prefix}VarExpr {loc}: {node.name}")

        elif isinstance(node, IntLiteralExpr):
            self.lines.append(f"{prefix}IntLiteral {loc}: {node.value}")

        else:
            self.lines.append(f"{prefix}{node.__class__.__name__} {loc}")

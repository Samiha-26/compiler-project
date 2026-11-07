"""Semantic analysis for C Minor validating types, scopes, and control flow."""

from __future__ import annotations
import sys
from typing import Dict, List, Optional, Tuple, Set

from cminor.diagnostics import (
    DiagnosticCode,
    DiagnosticEmitter,
    SourceLocation,
)
from cminor.parser.ast import (
    ASTNode,
    Program,
    FunctionDecl,
    FunctionDef,
    ParamDecl,
    VarDecl,
    BlockStmt,
    Statement,
    ExprStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
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
from cminor.sema.symbols import Symbol, SymbolKind, Scope


class SemanticAnalyzer:
    """Performs full semantic validation on the AST."""

    def __init__(self, emitter: Optional[DiagnosticEmitter] = None) -> None:
        self.emitter = emitter or DiagnosticEmitter(sys.stderr)
        self.global_scope = Scope(name="global", depth=0)
        self.current_scope: Scope = self.global_scope
        self.scope_counter = 0
        self.all_symbols: List[Symbol] = []
        self.loop_depth = 0
        self.current_function: Optional[Symbol] = None

    def _enter_scope(self, name: str) -> Scope:
        self.scope_counter += 1
        new_scope = Scope(
            name=f"{name}_{self.scope_counter}",
            depth=self.current_scope.depth + 1,
            parent=self.current_scope,
        )
        self.current_scope = new_scope
        return new_scope

    def _exit_scope(self) -> None:
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def analyze(self, program: Program) -> bool:
        """Runs all semantic checks on the program AST. Returns True if no errors."""
        # Pass 1: Collect and validate external declarations and definitions
        for ext in program.externals:
            if isinstance(ext, FunctionDecl):
                self._declare_function(ext)
            elif isinstance(ext, FunctionDef):
                self._define_function_header(ext)

        # Pass 2: Check function bodies and expressions
        for ext in program.externals:
            if isinstance(ext, FunctionDef):
                self._analyze_function_body(ext)

        # Pass 3: Check global program constraints (CM-LANG-002)
        # Exactly one int main(void)
        main_sym = self.global_scope.lookup_local("main")
        if not main_sym or not main_sym.is_defined:
            self.emitter.report(
                code=DiagnosticCode.NAME_ERROR,
                message="Program must define 'int main(void)'.",
                location=program.span.start,
            )
        else:
            if main_sym.type_name != "int" or len(main_sym.param_types) != 0:
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message="Function 'main' must have exact signature 'int main(void)'.",
                    location=main_sym.location,
                )

        # Check for any declared function without a definition (CM-LANG-002)
        for sym in self.global_scope.symbols.values():
            if sym.kind == SymbolKind.FUNCTION and not sym.is_defined:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Declared function '{sym.name}' has no definition in the compilation unit.",
                    location=sym.decl_location or sym.location,
                )

        return not self.emitter.has_errors()

    def _declare_function(self, decl: FunctionDecl) -> None:
        name = decl.name
        ret_type = decl.return_type.name

        # Parameter count check: 0 to 6 int parameters (CM-LANG-003)
        if len(decl.params) > 6:
            self.emitter.report(
                code=DiagnosticCode.CALL_ERROR,
                message=f"Function '{name}' has {len(decl.params)} parameters; maximum supported is 6.",
                location=decl.span.start,
            )

        param_types = [p.type_node.name for p in decl.params]
        param_names = [p.name or "" for p in decl.params]

        existing = self.global_scope.lookup_local(name)
        if existing:
            # Check compatibility
            if existing.type_name != ret_type or existing.param_types != param_types:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Conflicting declaration for function '{name}'.",
                    location=decl.span.start,
                    related_location=existing.location,
                    related_message="Previous declaration was here.",
                )
            return

        sym = Symbol(
            name=name,
            kind=SymbolKind.FUNCTION,
            type_name=ret_type,
            location=decl.span.start,
            scope_depth=0,
            scope_name="global",
            param_types=param_types,
            param_names=param_names,
            is_defined=False,
            decl_location=decl.span.start,
        )
        self.global_scope.define(sym)
        self.all_symbols.append(sym)

    def _define_function_header(self, defn: FunctionDef) -> None:
        name = defn.name
        ret_type = defn.return_type.name

        if len(defn.params) > 6:
            self.emitter.report(
                code=DiagnosticCode.CALL_ERROR,
                message=f"Function '{name}' has {len(defn.params)} parameters; maximum supported is 6.",
                location=defn.span.start,
            )

        param_types = [p.type_node.name for p in defn.params]
        param_names = [p.name or "" for p in defn.params]

        existing = self.global_scope.lookup_local(name)
        if existing:
            if existing.is_defined:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Redefinition of function '{name}'.",
                    location=defn.span.start,
                    related_location=existing.def_location or existing.location,
                    related_message="Previous definition was here.",
                )
                return

            if existing.type_name != ret_type or existing.param_types != param_types:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Definition of function '{name}' does not match its earlier declaration.",
                    location=defn.span.start,
                    related_location=existing.decl_location,
                    related_message="Previous declaration was here.",
                )
                return

            existing.is_defined = True
            existing.def_location = defn.span.start
            existing.param_names = param_names
        else:
            sym = Symbol(
                name=name,
                kind=SymbolKind.FUNCTION,
                type_name=ret_type,
                location=defn.span.start,
                scope_depth=0,
                scope_name="global",
                param_types=param_types,
                param_names=param_names,
                is_defined=True,
                decl_location=defn.span.start,
                def_location=defn.span.start,
            )
            self.global_scope.define(sym)
            self.all_symbols.append(sym)

    def _analyze_function_body(self, defn: FunctionDef) -> None:
        fn_sym = self.global_scope.lookup_local(defn.name)
        self.current_function = fn_sym

        # Enter function parameter scope
        fn_scope = self._enter_scope(f"fn_{defn.name}")

        # Define parameters in the function scope
        seen_params: Set[str] = set()
        for p in defn.params:
            if not p.name:
                continue
            if p.name in seen_params:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Duplicate parameter name '{p.name}' in function '{defn.name}'.",
                    location=p.span.start,
                )
            seen_params.add(p.name)

            param_sym = Symbol(
                name=p.name,
                kind=SymbolKind.PARAMETER,
                type_name="int",
                location=p.span.start,
                scope_depth=fn_scope.depth,
                scope_name=fn_scope.name,
            )
            fn_scope.define(param_sym)
            self.all_symbols.append(param_sym)

        # Check body items
        # Note: defn.body is a BlockStmt. We don't need a separate scope for the outermost block
        # or we can treat the block as a nested scope. But in C Minor, local variables in the function
        # can shadow outer scopes. To avoid parameter redeclaration conflict, the outer block
        # must check against parameter names: in C, parameters and top-level locals share scope!
        # Let's inspect defn.body items in the same scope or treat them properly:
        self._analyze_block(defn.body, is_function_root=True)

        # Course rule CM-STM-006:
        # "every int function, including main, shall have as its last top-level block item
        # an explicit return <int-expression>; statement."
        if fn_sym and fn_sym.type_name == "int":
            has_final_return = False
            if defn.body.items:
                last_item = defn.body.items[-1]
                if isinstance(last_item, ReturnStmt) and last_item.expr is not None:
                    has_final_return = True

            if not has_final_return:
                self.emitter.report(
                    code=DiagnosticCode.RETURN_ERROR,
                    message=f"Function '{defn.name}' missing explicit top-level final return statement.",
                    location=defn.body.span.end,
                )

        self._exit_scope()
        self.current_function = None

    def _analyze_block(self, block: BlockStmt, is_function_root: bool = False) -> None:
        if not is_function_root:
            self._enter_scope("block")

        for item in block.items:
            if isinstance(item, VarDecl):
                self._analyze_var_decl(item)
            elif isinstance(item, Statement):
                self._analyze_statement(item)

        if not is_function_root:
            self._exit_scope()

    def _analyze_var_decl(self, decl: VarDecl) -> None:
        # Variable name check in current scope (CM-LANG-004)
        existing = self.current_scope.lookup_local(decl.name)
        if existing:
            self.emitter.report(
                code=DiagnosticCode.NAME_ERROR,
                message=f"Redeclaration of variable '{decl.name}' in the same scope.",
                location=decl.span.start,
                related_location=existing.location,
                related_message="Previous declaration was here.",
            )
            return

        if decl.init:
            self._analyze_expr(decl.init)
            if decl.init.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message=f"Cannot initialize variable '{decl.name}' with void expression.",
                    location=decl.init.span.start,
                )

        sym = Symbol(
            name=decl.name,
            kind=SymbolKind.VARIABLE,
            type_name="int",
            location=decl.span.start,
            scope_depth=self.current_scope.depth,
            scope_name=self.current_scope.name,
        )
        self.current_scope.define(sym)
        self.all_symbols.append(sym)

    def _analyze_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, BlockStmt):
            self._analyze_block(stmt, is_function_root=False)

        elif isinstance(stmt, ExprStmt):
            if stmt.expr:
                self._analyze_expr(stmt.expr)

        elif isinstance(stmt, IfStmt):
            self._analyze_expr(stmt.cond)
            if stmt.cond.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message="Condition in 'if' statement must evaluate to int.",
                    location=stmt.cond.span.start,
                )
            self._analyze_statement(stmt.then_branch)
            if stmt.else_branch:
                self._analyze_statement(stmt.else_branch)

        elif isinstance(stmt, WhileStmt):
            self._analyze_expr(stmt.cond)
            if stmt.cond.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message="Condition in 'while' statement must evaluate to int.",
                    location=stmt.cond.span.start,
                )
            self.loop_depth += 1
            self._analyze_statement(stmt.body)
            self.loop_depth -= 1

        elif isinstance(stmt, ForStmt):
            # for (init; cond; step)
            # A for-declared variable lives through the loop body/update and is invisible afterward (CM-STM-002)
            self._enter_scope("for")
            if stmt.init:
                if isinstance(stmt.init, VarDecl):
                    self._analyze_var_decl(stmt.init)
                elif isinstance(stmt.init, ExprStmt) and stmt.init.expr:
                    self._analyze_expr(stmt.init.expr)

            if stmt.cond:
                self._analyze_expr(stmt.cond)
                if stmt.cond.inferred_type != "int":
                    self.emitter.report(
                        code=DiagnosticCode.TYPE_ERROR,
                        message="Condition in 'for' statement must evaluate to int.",
                        location=stmt.cond.span.start,
                    )

            if stmt.step:
                self._analyze_expr(stmt.step)

            self.loop_depth += 1
            self._analyze_statement(stmt.body)
            self.loop_depth -= 1

            self._exit_scope()

        elif isinstance(stmt, BreakStmt):
            if self.loop_depth <= 0:
                self.emitter.report(
                    code=DiagnosticCode.CONTROL_FLOW_ERROR,
                    message="'break' statement outside of loop.",
                    location=stmt.span.start,
                )

        elif isinstance(stmt, ContinueStmt):
            if self.loop_depth <= 0:
                self.emitter.report(
                    code=DiagnosticCode.CONTROL_FLOW_ERROR,
                    message="'continue' statement outside of loop.",
                    location=stmt.span.start,
                )

        elif isinstance(stmt, ReturnStmt):
            fn_ret = self.current_function.type_name if self.current_function else "int"
            if fn_ret == "void":
                if stmt.expr is not None:
                    self.emitter.report(
                        code=DiagnosticCode.RETURN_ERROR,
                        message="Void function cannot return an expression.",
                        location=stmt.span.start,
                    )
            else:
                if stmt.expr is None:
                    self.emitter.report(
                        code=DiagnosticCode.RETURN_ERROR,
                        message=f"Function returning '{fn_ret}' must return a value.",
                        location=stmt.span.start,
                    )
                else:
                    self._analyze_expr(stmt.expr)
                    if stmt.expr.inferred_type != "int":
                        self.emitter.report(
                            code=DiagnosticCode.RETURN_ERROR,
                            message="Return expression must evaluate to int.",
                            location=stmt.expr.span.start,
                        )

    def _analyze_expr(self, expr: Expr) -> None:
        if isinstance(expr, IntLiteralExpr):
            expr.inferred_type = "int"
            expr.is_lvalue = False

        elif isinstance(expr, VarExpr):
            sym = self.current_scope.lookup(expr.name)
            if not sym:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Undeclared identifier '{expr.name}'.",
                    location=expr.span.start,
                )
                expr.inferred_type = "int"
                expr.is_lvalue = False
                return

            if sym.kind == SymbolKind.FUNCTION:
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message=f"Function '{expr.name}' cannot be used as an ordinary variable.",
                    location=expr.span.start,
                )
                expr.inferred_type = "int"
                expr.is_lvalue = False
                return

            expr.inferred_type = sym.type_name
            expr.is_lvalue = True

        elif isinstance(expr, CallExpr):
            sym = self.global_scope.lookup_local(expr.callee)
            if not sym or sym.kind != SymbolKind.FUNCTION:
                self.emitter.report(
                    code=DiagnosticCode.NAME_ERROR,
                    message=f"Call to undeclared function '{expr.callee}'.",
                    location=expr.span.start,
                )
                expr.inferred_type = "int"
                expr.is_lvalue = False
                return

            # Arity check (CM-SEM-004)
            expected_count = len(sym.param_types)
            actual_count = len(expr.args)
            if expected_count != actual_count:
                self.emitter.report(
                    code=DiagnosticCode.CALL_ERROR,
                    message=f"Function '{expr.callee}' expects {expected_count} arguments, but got {actual_count}.",
                    location=expr.span.start,
                    related_location=sym.location,
                    related_message="Function declared here.",
                )

            # Analyze arguments
            for arg in expr.args:
                self._analyze_expr(arg)
                if arg.inferred_type != "int":
                    self.emitter.report(
                        code=DiagnosticCode.TYPE_ERROR,
                        message=f"Argument in call to '{expr.callee}' cannot be void.",
                        location=arg.span.start,
                    )

            expr.inferred_type = sym.type_name
            expr.is_lvalue = False

        elif isinstance(expr, UnaryExpr):
            self._analyze_expr(expr.operand)
            if expr.operand.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message=f"Operand of unary '{expr.op}' must be int.",
                    location=expr.operand.span.start,
                )
            expr.inferred_type = "int"
            expr.is_lvalue = False

        elif isinstance(expr, BinaryExpr):
            self._analyze_expr(expr.left)
            self._analyze_expr(expr.right)
            if expr.left.inferred_type != "int" or expr.right.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message=f"Operands of binary '{expr.op}' must be int.",
                    location=expr.span.start,
                )
            expr.inferred_type = "int"
            expr.is_lvalue = False

        elif isinstance(expr, AssignExpr):
            self._analyze_expr(expr.target)
            self._analyze_expr(expr.value)

            # Target must be an lvalue (CM-SEM-003, CM-EXP-002)
            if not expr.target.is_lvalue:
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message="Left-hand side of assignment must be a modifiable variable.",
                    location=expr.target.span.start,
                )

            if expr.value.inferred_type != "int":
                self.emitter.report(
                    code=DiagnosticCode.TYPE_ERROR,
                    message="Right-hand side of assignment cannot be void.",
                    location=expr.value.span.start,
                )

            expr.inferred_type = "int"
            expr.is_lvalue = True

        else:
            expr.inferred_type = "int"
            expr.is_lvalue = False

    def dump_symbols(self) -> str:
        """Produces deterministic, inspectable table for --dump-symbols (CM-SEM-006)."""
        lines = [
            "================================ Symbol Table ================================",
            f"{'Name':<16} {'Kind':<12} {'Type/Sig':<18} {'Scope':<24} {'Location'}",
            "------------------------------------------------------------------------------",
        ]
        # Sort or display in insertion order
        for sym in self.all_symbols:
            lines.append(sym.format_entry())
        return "\n".join(lines)

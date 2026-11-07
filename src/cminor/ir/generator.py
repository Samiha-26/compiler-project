"""Intermediate Representation generator converting AST to Student Three-Address Code."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from cminor.parser.ast import (
    Program,
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
from cminor.ir.instructions import (
    Operand,
    Constant,
    Variable,
    Temporary,
    IRInstruction,
    LabelInstr,
    AssignInstr,
    BinOpInstr,
    UnaryOpInstr,
    JumpInstr,
    BranchIfZeroInstr,
    BranchIfNotZeroInstr,
    ParamInstr,
    CallInstr,
    ReturnInstr,
    IRFunction,
    IRProgram,
)


class LoopContext:
    def __init__(self, break_label: str, continue_label: str) -> None:
        self.break_label = break_label
        self.continue_label = continue_label


class IRGenerator:
    """Generates Three-Address Code IR from AST."""

    def __init__(self) -> None:
        self.temp_counter = 0
        self.label_counter = 0
        self.var_counter = 0
        self.scopes: List[Dict[str, Variable]] = []
        self.loop_stack: List[LoopContext] = []
        self.current_instructions: List[IRInstruction] = []
        self.current_locals: List[Variable] = []
        self.functions: List[IRFunction] = []

    def _new_temp(self) -> Temporary:
        self.temp_counter += 1
        return Temporary(id=self.temp_counter)

    def _new_label(self, hint: str = "L") -> str:
        self.label_counter += 1
        return f".{hint}{self.label_counter}"

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _define_var(self, name: str) -> Variable:
        self.var_counter += 1
        var = Variable(name=name, unique_id=self.var_counter)
        self.scopes[-1][name] = var
        self.current_locals.append(var)
        return var

    def _resolve_var(self, name: str) -> Variable:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise RuntimeError(f"Unresolved variable in IR generation: {name}")

    def _emit(self, instr: IRInstruction) -> None:
        self.current_instructions.append(instr)

    def generate(self, program: Program) -> IRProgram:
        self.functions.clear()
        for ext in program.externals:
            if isinstance(ext, FunctionDef):
                self._generate_function(ext)
        return IRProgram(functions=list(self.functions))

    def _generate_function(self, defn: FunctionDef) -> None:
        self.current_instructions = []
        self.current_locals = []
        self.scopes = []
        self.loop_stack = []

        self._push_scope()

        # Define parameters
        params: List[Variable] = []
        for p in defn.params:
            if p.name:
                var = self._define_var(p.name)
                params.append(var)

        # Generate body
        for item in defn.body.items:
            if isinstance(item, VarDecl):
                self._generate_var_decl(item)
            elif isinstance(item, Statement):
                self._generate_statement(item)

        self._pop_scope()

        # Add function to program
        ir_fn = IRFunction(
            name=defn.name,
            return_type=defn.return_type.name,
            params=params,
            locals=list(self.current_locals),
            instructions=list(self.current_instructions),
        )
        self.functions.append(ir_fn)

    def _generate_var_decl(self, decl: VarDecl) -> None:
        var = self._define_var(decl.name)
        if decl.init:
            init_val = self._generate_expr(decl.init)
            if init_val:
                self._emit(AssignInstr(dest=var, src=init_val))

    def _generate_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, BlockStmt):
            self._push_scope()
            for item in stmt.items:
                if isinstance(item, VarDecl):
                    self._generate_var_decl(item)
                elif isinstance(item, Statement):
                    self._generate_statement(item)
            self._pop_scope()

        elif isinstance(stmt, ExprStmt):
            if stmt.expr:
                self._generate_expr(stmt.expr)

        elif isinstance(stmt, IfStmt):
            cond_val = self._generate_expr(stmt.cond)
            l_else = self._new_label("L_else") if stmt.else_branch else None
            l_end = self._new_label("L_endif")

            target_if_false = l_else if l_else else l_end
            self._emit(BranchIfZeroInstr(cond=cond_val, target=target_if_false))

            self._generate_statement(stmt.then_branch)

            if stmt.else_branch:
                self._emit(JumpInstr(target=l_end))
                self._emit(LabelInstr(name=l_else))
                self._generate_statement(stmt.else_branch)

            self._emit(LabelInstr(name=l_end))

        elif isinstance(stmt, WhileStmt):
            l_cond = self._new_label("L_while_cond")
            l_body = self._new_label("L_while_body")
            l_end = self._new_label("L_while_end")

            self.loop_stack.append(LoopContext(break_label=l_end, continue_label=l_cond))

            self._emit(LabelInstr(name=l_cond))
            cond_val = self._generate_expr(stmt.cond)
            self._emit(BranchIfZeroInstr(cond=cond_val, target=l_end))

            self._emit(LabelInstr(name=l_body))
            self._generate_statement(stmt.body)
            self._emit(JumpInstr(target=l_cond))

            self._emit(LabelInstr(name=l_end))
            self.loop_stack.pop()

        elif isinstance(stmt, ForStmt):
            self._push_scope()
            if stmt.init:
                if isinstance(stmt.init, VarDecl):
                    self._generate_var_decl(stmt.init)
                elif isinstance(stmt.init, ExprStmt) and stmt.init.expr:
                    self._generate_expr(stmt.init.expr)

            l_cond = self._new_label("L_for_cond")
            l_body = self._new_label("L_for_body")
            l_update = self._new_label("L_for_update")
            l_end = self._new_label("L_for_end")

            self.loop_stack.append(LoopContext(break_label=l_end, continue_label=l_update))

            self._emit(LabelInstr(name=l_cond))
            if stmt.cond:
                cond_val = self._generate_expr(stmt.cond)
                self._emit(BranchIfZeroInstr(cond=cond_val, target=l_end))

            self._emit(LabelInstr(name=l_body))
            self._generate_statement(stmt.body)

            self._emit(LabelInstr(name=l_update))
            if stmt.step:
                self._generate_expr(stmt.step)
            self._emit(JumpInstr(target=l_cond))

            self._emit(LabelInstr(name=l_end))
            self.loop_stack.pop()
            self._pop_scope()

        elif isinstance(stmt, BreakStmt):
            target = self.loop_stack[-1].break_label
            self._emit(JumpInstr(target=target))

        elif isinstance(stmt, ContinueStmt):
            target = self.loop_stack[-1].continue_label
            self._emit(JumpInstr(target=target))

        elif isinstance(stmt, ReturnStmt):
            if stmt.expr:
                ret_val = self._generate_expr(stmt.expr)
                self._emit(ReturnInstr(value=ret_val))
            else:
                self._emit(ReturnInstr(value=None))

    def _generate_expr(self, expr: Expr) -> Optional[Operand]:
        if isinstance(expr, IntLiteralExpr):
            return Constant(value=expr.value)

        elif isinstance(expr, VarExpr):
            return self._resolve_var(expr.name)

        elif isinstance(expr, AssignExpr):
            # CM-EXP-006: assignment evaluates its right operand before storing to identifier
            rhs_val = self._generate_expr(expr.value)
            # Find destination variable
            if isinstance(expr.target, VarExpr):
                lhs_var = self._resolve_var(expr.target.name)
            else:
                raise RuntimeError("Non-variable assignment target in IR generation")

            self._emit(AssignInstr(dest=lhs_var, src=rhs_val))
            return lhs_var

        elif isinstance(expr, BinaryExpr):
            # Short-circuit logical operators (CM-EXP-005)
            if expr.op == "&&":
                return self._generate_short_circuit_and(expr)
            elif expr.op == "||":
                return self._generate_short_circuit_or(expr)

            # Standard binary operators (left-to-right evaluation)
            left_val = self._generate_expr(expr.left)
            right_val = self._generate_expr(expr.right)
            dest = self._new_temp()
            self._emit(BinOpInstr(dest=dest, op=expr.op, left=left_val, right=right_val))
            return dest

        elif isinstance(expr, UnaryExpr):
            opnd_val = self._generate_expr(expr.operand)
            if expr.op == "+":
                return opnd_val
            dest = self._new_temp()
            self._emit(UnaryOpInstr(dest=dest, op=expr.op, operand=opnd_val))
            return dest

        elif isinstance(expr, CallExpr):
            # Evaluate arguments left to right (CM-EXP-006)
            arg_vals = [self._generate_expr(arg) for arg in expr.args]
            for val in arg_vals:
                self._emit(ParamInstr(arg=val))

            if expr.inferred_type == "void":
                self._emit(CallInstr(dest=None, callee=expr.callee, arg_count=len(arg_vals)))
                return None
            else:
                dest = self._new_temp()
                self._emit(CallInstr(dest=dest, callee=expr.callee, arg_count=len(arg_vals)))
                return dest

        return None

    def _generate_short_circuit_and(self, expr: BinaryExpr) -> Operand:
        result_var = self._new_temp()
        l_false = self._new_label("L_and_false")
        l_end = self._new_label("L_and_end")

        left_val = self._generate_expr(expr.left)
        self._emit(BranchIfZeroInstr(cond=left_val, target=l_false))

        right_val = self._generate_expr(expr.right)
        cond_check = self._new_temp()
        self._emit(BinOpInstr(dest=cond_check, op="!=", left=right_val, right=Constant(0)))
        self._emit(AssignInstr(dest=result_var, src=cond_check))
        self._emit(JumpInstr(target=l_end))

        self._emit(LabelInstr(name=l_false))
        self._emit(AssignInstr(dest=result_var, src=Constant(0)))

        self._emit(LabelInstr(name=l_end))
        return result_var

    def _generate_short_circuit_or(self, expr: BinaryExpr) -> Operand:
        result_var = self._new_temp()
        l_true = self._new_label("L_or_true")
        l_end = self._new_label("L_or_end")

        left_val = self._generate_expr(expr.left)
        self._emit(BranchIfNotZeroInstr(cond=left_val, target=l_true))

        right_val = self._generate_expr(expr.right)
        cond_check = self._new_temp()
        self._emit(BinOpInstr(dest=cond_check, op="!=", left=right_val, right=Constant(0)))
        self._emit(AssignInstr(dest=result_var, src=cond_check))
        self._emit(JumpInstr(target=l_end))

        self._emit(LabelInstr(name=l_true))
        self._emit(AssignInstr(dest=result_var, src=Constant(1)))

        self._emit(LabelInstr(name=l_end))
        return result_var

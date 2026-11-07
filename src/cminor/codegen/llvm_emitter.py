"""Textual LLVM IR (.ll) code generator from Student IR."""

from __future__ import annotations
from typing import Dict, List, Optional, Set

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


class LLVMEmitter:
    """Emits valid textual LLVM IR (target x86_64-pc-linux-gnu)."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.var_ptrs: Dict[str, str] = {}
        self.param_regs: List[str] = []
        self.reg_counter = 0

    def _new_reg(self) -> str:
        self.reg_counter += 1
        return f"%r{self.reg_counter}"

    def emit(self, ir_prog: IRProgram) -> str:
        self.lines = [
            '; ModuleID = "cminor"',
            'source_filename = "cminor"',
            'target triple = "x86_64-pc-linux-gnu"',
            "",
        ]

        # Declare external / forward functions if any
        all_defined_names = {fn.name for fn in ir_prog.functions}
        called_functions: Set[Tuple[str, int, str]] = set()

        for fn in ir_prog.functions:
            for instr in fn.instructions:
                if isinstance(instr, CallInstr):
                    called_functions.add((instr.callee, instr.arg_count, "i32" if instr.dest else "void"))

        for callee, arg_count, ret_ty in sorted(called_functions):
            if callee not in all_defined_names:
                args_ty = ", ".join(["i32"] * arg_count)
                self.lines.append(f"declare {ret_ty} @{callee}({args_ty})")

        if called_functions and any(c not in all_defined_names for c, _, _ in called_functions):
            self.lines.append("")

        for fn in ir_prog.functions:
            self._emit_function(fn)
            self.lines.append("")

        return "\n".join(self.lines)

    def _emit_function(self, fn: IRFunction) -> None:
        self.var_ptrs = {}
        self.reg_counter = 0

        ret_type = "i32" if fn.return_type == "int" else "void"
        param_list = []
        for i, p in enumerate(fn.params):
            param_list.append(f"i32 %arg_{i}")

        params_sig = ", ".join(param_list)
        self.lines.append(f"define {ret_type} @{fn.name}({params_sig}) {{")
        self.lines.append("entry:")

        # Allocate space on stack for parameters and local variables
        for i, p in enumerate(fn.params):
            ptr = f"%ptr_{p.name}_{p.unique_id}"
            self.var_ptrs[p.format()] = ptr
            self.lines.append(f"    {ptr} = alloca i32, align 4")
            self.lines.append(f"    store i32 %arg_{i}, ptr {ptr}, align 4")

        for loc in fn.locals:
            if loc.format() not in self.var_ptrs:
                ptr = f"%ptr_{loc.name}_{loc.unique_id}"
                self.var_ptrs[loc.format()] = ptr
                self.lines.append(f"    {ptr} = alloca i32, align 4")
                self.lines.append(f"    store i32 0, ptr {ptr}, align 4")

        # Map temporaries to LLVM registers
        temp_map: Dict[str, str] = {}
        pending_params: List[str] = []

        # Track basic block termination
        has_terminator = False

        for instr in fn.instructions:
            if isinstance(instr, LabelInstr):
                lbl_name = instr.name.lstrip(".")
                if not has_terminator:
                    self.lines.append(f"    br label %{lbl_name}")
                self.lines.append(f"{lbl_name}:")
                has_terminator = False

            elif isinstance(instr, AssignInstr):
                val_reg = self._operand_to_reg(instr.src, temp_map)
                if isinstance(instr.dest, Variable):
                    ptr = self.var_ptrs[instr.dest.format()]
                    self.lines.append(f"    store i32 {val_reg}, ptr {ptr}, align 4")
                elif isinstance(instr.dest, Temporary):
                    temp_map[instr.dest.format()] = val_reg

            elif isinstance(instr, BinOpInstr):
                left_reg = self._operand_to_reg(instr.left, temp_map)
                right_reg = self._operand_to_reg(instr.right, temp_map)
                dest_reg = self._new_reg()

                if instr.op == "+":
                    self.lines.append(f"    {dest_reg} = add nsw i32 {left_reg}, {right_reg}")
                elif instr.op == "-":
                    self.lines.append(f"    {dest_reg} = sub nsw i32 {left_reg}, {right_reg}")
                elif instr.op == "*":
                    self.lines.append(f"    {dest_reg} = mul nsw i32 {left_reg}, {right_reg}")
                elif instr.op == "/":
                    self.lines.append(f"    {dest_reg} = sdiv i32 {left_reg}, {right_reg}")
                elif instr.op == "%":
                    self.lines.append(f"    {dest_reg} = srem i32 {left_reg}, {right_reg}")
                elif instr.op in ("<", "<=", ">", ">=", "==", "!="):
                    cmp_map = {
                        "<": "slt",
                        "<=": "sle",
                        ">": "sgt",
                        ">=": "sge",
                        "==": "eq",
                        "!=": "ne",
                    }
                    cmp_reg = self._new_reg()
                    self.lines.append(f"    {cmp_reg} = icmp {cmp_map[instr.op]} i32 {left_reg}, {right_reg}")
                    self.lines.append(f"    {dest_reg} = zext i1 {cmp_reg} to i32")

                temp_map[instr.dest.format()] = dest_reg

            elif isinstance(instr, UnaryOpInstr):
                opnd_reg = self._operand_to_reg(instr.operand, temp_map)
                dest_reg = self._new_reg()
                if instr.op == "-":
                    self.lines.append(f"    {dest_reg} = sub nsw i32 0, {opnd_reg}")
                elif instr.op == "!":
                    cmp_reg = self._new_reg()
                    self.lines.append(f"    {cmp_reg} = icmp eq i32 {opnd_reg}, 0")
                    self.lines.append(f"    {dest_reg} = zext i1 {cmp_reg} to i32")
                elif instr.op == "+":
                    dest_reg = opnd_reg
                temp_map[instr.dest.format()] = dest_reg

            elif isinstance(instr, ParamInstr):
                p_reg = self._operand_to_reg(instr.arg, temp_map)
                pending_params.append(f"i32 {p_reg}")

            elif isinstance(instr, CallInstr):
                args_str = ", ".join(pending_params)
                pending_params = []
                if instr.dest:
                    call_reg = self._new_reg()
                    self.lines.append(f"    {call_reg} = call i32 @{instr.callee}({args_str})")
                    temp_map[instr.dest.format()] = call_reg
                else:
                    self.lines.append(f"    call void @{instr.callee}({args_str})")

            elif isinstance(instr, JumpInstr):
                lbl_name = instr.target.lstrip(".")
                self.lines.append(f"    br label %{lbl_name}")
                has_terminator = True

            elif isinstance(instr, BranchIfZeroInstr):
                cond_reg = self._operand_to_reg(instr.cond, temp_map)
                cmp_reg = self._new_reg()
                self.lines.append(f"    {cmp_reg} = icmp eq i32 {cond_reg}, 0")
                lbl_false = instr.target.lstrip(".")
                lbl_fall = self._new_reg().lstrip("%")
                self.lines.append(f"    br i1 {cmp_reg}, label %{lbl_false}, label %{lbl_fall}")
                self.lines.append(f"{lbl_fall}:")
                has_terminator = False

            elif isinstance(instr, BranchIfNotZeroInstr):
                cond_reg = self._operand_to_reg(instr.cond, temp_map)
                cmp_reg = self._new_reg()
                self.lines.append(f"    {cmp_reg} = icmp ne i32 {cond_reg}, 0")
                lbl_true = instr.target.lstrip(".")
                lbl_fall = self._new_reg().lstrip("%")
                self.lines.append(f"    br i1 {cmp_reg}, label %{lbl_true}, label %{lbl_fall}")
                self.lines.append(f"{lbl_fall}:")
                has_terminator = False

            elif isinstance(instr, ReturnInstr):
                if instr.value:
                    val_reg = self._operand_to_reg(instr.value, temp_map)
                    self.lines.append(f"    ret i32 {val_reg}")
                else:
                    self.lines.append("    ret void")
                has_terminator = True

        if not has_terminator:
            if ret_type == "void":
                self.lines.append("    ret void")
            else:
                self.lines.append("    ret i32 0")

        self.lines.append("}")

    def _operand_to_reg(self, op: Operand, temp_map: Dict[str, str]) -> str:
        if isinstance(op, Constant):
            return str(op.value)

        elif isinstance(op, Variable):
            ptr = self.var_ptrs[op.format()]
            load_reg = self._new_reg()
            self.lines.append(f"    {load_reg} = load i32, ptr {ptr}, align 4")
            return load_reg

        elif isinstance(op, Temporary):
            if op.format() in temp_map:
                return temp_map[op.format()]
            # If not mapped yet, allocate
            reg = self._new_reg()
            temp_map[op.format()] = reg
            return reg

        return "0"

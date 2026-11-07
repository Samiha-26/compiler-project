"""Textual QBE Intermediate Language (.ssa) code generator from Student IR."""

from __future__ import annotations
from typing import Dict, List, Optional

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


class QBEEmitter:
    """Emits valid textual QBE IL (target amd64_sysv)."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.var_ptrs: Dict[str, str] = {}
        self.reg_counter = 0

    def _new_reg(self) -> str:
        self.reg_counter += 1
        return f"%q{self.reg_counter}"

    def emit(self, ir_prog: IRProgram) -> str:
        self.lines = []
        for fn in ir_prog.functions:
            self._emit_function(fn)
            self.lines.append("")
        return "\n".join(self.lines)

    def _emit_function(self, fn: IRFunction) -> None:
        self.var_ptrs = {}
        self.reg_counter = 0

        fn_type_marker = "w " if fn.return_type == "int" else ""
        param_list = [f"w %arg_{i}" for i in range(len(fn.params))]
        params_sig = ", ".join(param_list)

        self.lines.append(f"export function {fn_type_marker}${fn.name}({params_sig}) {{")
        self.lines.append("@start")

        # Allocations
        for i, p in enumerate(fn.params):
            ptr = f"%ptr_{p.name}_{p.unique_id}"
            self.var_ptrs[p.format()] = ptr
            self.lines.append(f"    {ptr} =l alloc4 4")
            self.lines.append(f"    storew %arg_{i}, {ptr}")

        for loc in fn.locals:
            if loc.format() not in self.var_ptrs:
                ptr = f"%ptr_{loc.name}_{loc.unique_id}"
                self.var_ptrs[loc.format()] = ptr
                self.lines.append(f"    {ptr} =l alloc4 4")
                self.lines.append(f"    storew 0, {ptr}")

        temp_map: Dict[str, str] = {}
        pending_params: List[str] = []
        has_terminator = False

        for instr in fn.instructions:
            if isinstance(instr, LabelInstr):
                lbl_name = instr.name.replace(".", "")
                if not has_terminator:
                    self.lines.append(f"    jmp @{lbl_name}")
                self.lines.append(f"@{lbl_name}")
                has_terminator = False

            elif isinstance(instr, AssignInstr):
                val_reg = self._operand_to_reg(instr.src, temp_map)
                if isinstance(instr.dest, Variable):
                    ptr = self.var_ptrs[instr.dest.format()]
                    self.lines.append(f"    storew {val_reg}, {ptr}")
                elif isinstance(instr.dest, Temporary):
                    temp_map[instr.dest.format()] = val_reg

            elif isinstance(instr, BinOpInstr):
                left_reg = self._operand_to_reg(instr.left, temp_map)
                right_reg = self._operand_to_reg(instr.right, temp_map)
                dest_reg = self._new_reg()

                op_map = {
                    "+": "add",
                    "-": "sub",
                    "*": "mul",
                    "/": "div",
                    "%": "rem",
                    "<": "csltw",
                    "<=": "cslew",
                    ">": "csgtw",
                    ">=": "csgew",
                    "==": "ceqw",
                    "!=": "cnew",
                }
                qbe_op = op_map[instr.op]
                self.lines.append(f"    {dest_reg} =w {qbe_op} {left_reg}, {right_reg}")
                temp_map[instr.dest.format()] = dest_reg

            elif isinstance(instr, UnaryOpInstr):
                opnd_reg = self._operand_to_reg(instr.operand, temp_map)
                dest_reg = self._new_reg()
                if instr.op == "-":
                    self.lines.append(f"    {dest_reg} =w sub 0, {opnd_reg}")
                elif instr.op == "!":
                    self.lines.append(f"    {dest_reg} =w ceqw {opnd_reg}, 0")
                elif instr.op == "+":
                    dest_reg = opnd_reg
                temp_map[instr.dest.format()] = dest_reg

            elif isinstance(instr, ParamInstr):
                p_reg = self._operand_to_reg(instr.arg, temp_map)
                pending_params.append(f"w {p_reg}")

            elif isinstance(instr, CallInstr):
                args_str = ", ".join(pending_params)
                pending_params = []
                if instr.dest:
                    call_reg = self._new_reg()
                    self.lines.append(f"    {call_reg} =w call ${instr.callee}({args_str})")
                    temp_map[instr.dest.format()] = call_reg
                else:
                    self.lines.append(f"    call ${instr.callee}({args_str})")

            elif isinstance(instr, JumpInstr):
                lbl_name = instr.target.replace(".", "")
                self.lines.append(f"    jmp @{lbl_name}")
                has_terminator = True

            elif isinstance(instr, BranchIfZeroInstr):
                cond_reg = self._operand_to_reg(instr.cond, temp_map)
                lbl_target = instr.target.replace(".", "")
                lbl_fall = self._new_reg().replace("%", "")
                self.lines.append(f"    jnz {cond_reg}, @{lbl_fall}, @{lbl_target}")
                self.lines.append(f"@{lbl_fall}")
                has_terminator = False

            elif isinstance(instr, BranchIfNotZeroInstr):
                cond_reg = self._operand_to_reg(instr.cond, temp_map)
                lbl_target = instr.target.replace(".", "")
                lbl_fall = self._new_reg().replace("%", "")
                self.lines.append(f"    jnz {cond_reg}, @{lbl_target}, @{lbl_fall}")
                self.lines.append(f"@{lbl_fall}")
                has_terminator = False

            elif isinstance(instr, ReturnInstr):
                if instr.value:
                    val_reg = self._operand_to_reg(instr.value, temp_map)
                    self.lines.append(f"    ret {val_reg}")
                else:
                    self.lines.append("    ret")
                has_terminator = True

        if not has_terminator:
            if fn.return_type == "void":
                self.lines.append("    ret")
            else:
                self.lines.append("    ret 0")

        self.lines.append("}")

    def _operand_to_reg(self, op: Operand, temp_map: Dict[str, str]) -> str:
        if isinstance(op, Constant):
            return str(op.value)

        elif isinstance(op, Variable):
            ptr = self.var_ptrs[op.format()]
            load_reg = self._new_reg()
            self.lines.append(f"    {load_reg} =w loadw {ptr}")
            return load_reg

        elif isinstance(op, Temporary):
            if op.format() in temp_map:
                return temp_map[op.format()]
            reg = self._new_reg()
            temp_map[op.format()] = reg
            return reg

        return "0"

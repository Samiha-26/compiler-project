"""Three-Address Code (TAC) Intermediate Representation for C Minor."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


# -------------------------------------------------------------
# Operands
# -------------------------------------------------------------
@dataclass(frozen=True)
class Operand:
    def format(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Constant(Operand):
    value: int

    def format(self) -> str:
        return f"${self.value}"


@dataclass(frozen=True)
class Variable(Operand):
    name: str
    unique_id: int

    def format(self) -> str:
        return f"%{self.name}_{self.unique_id}"


@dataclass(frozen=True)
class Temporary(Operand):
    id: int

    def format(self) -> str:
        return f"$t{self.id}"


# -------------------------------------------------------------
# IR Instructions
# -------------------------------------------------------------
@dataclass
class IRInstruction:
    def format(self) -> str:
        raise NotImplementedError


@dataclass
class LabelInstr(IRInstruction):
    name: str

    def format(self) -> str:
        return f"{self.name}:"


@dataclass
class AssignInstr(IRInstruction):
    dest: Operand
    src: Operand

    def format(self) -> str:
        return f"    {self.dest.format()} = {self.src.format()}"


@dataclass
class BinOpInstr(IRInstruction):
    dest: Operand
    op: str
    left: Operand
    right: Operand

    def format(self) -> str:
        return f"    {self.dest.format()} = {self.left.format()} {self.op} {self.right.format()}"


@dataclass
class UnaryOpInstr(IRInstruction):
    dest: Operand
    op: str
    operand: Operand

    def format(self) -> str:
        return f"    {self.dest.format()} = {self.op} {self.operand.format()}"


@dataclass
class JumpInstr(IRInstruction):
    target: str

    def format(self) -> str:
        return f"    jump {self.target}"


@dataclass
class BranchIfZeroInstr(IRInstruction):
    cond: Operand
    target: str

    def format(self) -> str:
        return f"    br_zero {self.cond.format()}, {self.target}"


@dataclass
class BranchIfNotZeroInstr(IRInstruction):
    cond: Operand
    target: str

    def format(self) -> str:
        return f"    br_nonzero {self.cond.format()}, {self.target}"


@dataclass
class ParamInstr(IRInstruction):
    arg: Operand

    def format(self) -> str:
        return f"    param {self.arg.format()}"


@dataclass
class CallInstr(IRInstruction):
    dest: Optional[Operand]
    callee: str
    arg_count: int

    def format(self) -> str:
        if self.dest:
            return f"    {self.dest.format()} = call @{self.callee}({self.arg_count})"
        return f"    call @{self.callee}({self.arg_count})"


@dataclass
class ReturnInstr(IRInstruction):
    value: Optional[Operand]

    def format(self) -> str:
        if self.value:
            return f"    return {self.value.format()}"
        return "    return"


# -------------------------------------------------------------
# Function & Program
# -------------------------------------------------------------
@dataclass
class IRFunction:
    name: str
    return_type: str
    params: List[Variable]
    locals: List[Variable]
    instructions: List[IRInstruction]

    def format(self) -> str:
        param_str = ", ".join(p.format() for p in self.params)
        lines = [f"function {self.return_type} @{self.name}({param_str}):"]
        for instr in self.instructions:
            lines.append(instr.format())
        return "\n".join(lines)


@dataclass
class IRProgram:
    functions: List[IRFunction]

    def format(self) -> str:
        return "\n\n".join(fn.format() for fn in self.functions)

"""C Minor Intermediate Representation (IR) module."""

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
from cminor.ir.generator import IRGenerator

__all__ = [
    "Operand",
    "Constant",
    "Variable",
    "Temporary",
    "IRInstruction",
    "LabelInstr",
    "AssignInstr",
    "BinOpInstr",
    "UnaryOpInstr",
    "JumpInstr",
    "BranchIfZeroInstr",
    "BranchIfNotZeroInstr",
    "ParamInstr",
    "CallInstr",
    "ReturnInstr",
    "IRFunction",
    "IRProgram",
    "IRGenerator",
]

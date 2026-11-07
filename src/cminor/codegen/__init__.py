"""C Minor backend code generation module."""

from cminor.codegen.llvm_emitter import LLVMEmitter
from cminor.codegen.qbe_emitter import QBEEmitter

__all__ = ["LLVMEmitter", "QBEEmitter"]

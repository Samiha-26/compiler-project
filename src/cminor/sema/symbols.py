"""Symbol table and symbol representation for C Minor semantic analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from cminor.diagnostics import SourceLocation


class SymbolKind(Enum):
    VARIABLE = auto()
    PARAMETER = auto()
    FUNCTION = auto()


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    type_name: str  # "int" or "void"
    location: SourceLocation
    scope_depth: int
    scope_name: str

    # Function-specific fields
    param_types: List[str] = field(default_factory=list)
    param_names: List[str] = field(default_factory=list)
    is_defined: bool = False
    decl_location: Optional[SourceLocation] = None
    def_location: Optional[SourceLocation] = None

    def signature_str(self) -> str:
        if self.kind == SymbolKind.FUNCTION:
            params = ", ".join(self.param_types) if self.param_types else "void"
            return f"{self.type_name} ({params})"
        return self.type_name

    def format_entry(self) -> str:
        loc = f"{self.location.line}:{self.location.column}"
        kind_str = self.kind.name.lower()
        sig = self.signature_str()
        scope_str = f"scope={self.scope_name}(depth={self.scope_depth})"
        status = ""
        if self.kind == SymbolKind.FUNCTION:
            status = " [defined]" if self.is_defined else " [declared]"
        return f"{self.name:<16} {kind_str:<12} {sig:<18} {scope_str:<24} loc=<{loc}>{status}"


class Scope:
    """A single lexical scope level."""

    def __init__(self, name: str, depth: int, parent: Optional[Scope] = None) -> None:
        self.name = name
        self.depth = depth
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Defines a symbol in the current scope. Returns False if already declared in this scope."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

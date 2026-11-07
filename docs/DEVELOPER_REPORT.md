# C Minor Compiler (`cminorcc`) — Developer Report

This report documents the architectural design, algorithmic structures, intermediate representations, lowering pipelines, and error handling strategies implemented in the C Minor compiler.

---

## 1. Architectural Overview

The compiler is organized as an end-to-end, multi-stage pipeline:

```text
Source Text (.cm / .c)
    │
    ▼ [Lexer: src/cminor/lexer/scanner.py]
Token Stream
    │
    ▼ [Parser: src/cminor/parser/parser.py]
Abstract Syntax Tree (AST) [src/cminor/parser/ast.py]
    │
    ▼ [Semantic Analyzer: src/cminor/sema/analyzer.py]
Decorated AST & Scoped Symbol Tables [src/cminor/sema/symbols.py]
    │
    ▼ [IR Generator: src/cminor/ir/generator.py]
Student Three-Address Code (TAC) [src/cminor/ir/instructions.py]
    │
    ├─────────────────────────────┐
    ▼                             ▼
LLVM IR Emitter               QBE IL Emitter
[src/cminor/codegen/llvm_emitter.py] [src/cminor/codegen/qbe_emitter.py]
    │                             │
    ▼                             ▼
LLVM llc (.s)                 QBE qbe (.s)
```

---

## 2. Lexical Analysis (`src/cminor/lexer/`)

- **Token Model**: Tokens encapsulate a `TokenType` enum, literal string `lexeme`, 1-based source location `SourceSpan`, and parsed numeric `value`.
- **Position Tracking**: 1-based line and column coordinates are updated monotonically. Newlines (`\n` and `\r\n`) increment the line and reset the column to 1.
- **Preprocessing Directive Detection (`CM-LEX-005`)**:
  Lines track `at_line_start` status. The first non-whitespace, non-comment occurrence of `#` or `%:` triggers `UNSUPPORTED_PREPROCESSING_DIRECTIVE` without invoking external preprocessors.
- **Line Splicing Rejection (`CM-LEX-006`)**:
  A backslash immediately preceding a newline (`\` + `\n` or `\` + `\r\n`) raises `UNSUPPORTED_LINE_SPLICING`.
- **Comment Handling (`CM-LEX-003`)**:
  Block comments (`/* ... */`) and line comments (`//`) preserve token boundaries (e.g. `int/**/b` produces `int` then `b`). Unterminated comments are caught as `LEXICAL_ERROR`.
- **Literal Restrictions (`CM-LEX-002`)**:
  Hexadecimal (`0x`), binary (`0b`), octal/leading-zero numbers (`012`), floats (`1.0`), and out-of-range integers ($> 2^{31}-1$) are rejected with `UNSUPPORTED_FEATURE`.

---

## 3. Syntax Analysis & AST (`src/cminor/parser/`)

- **Recursive Descent Strategy**: The parser directly mirrors the EBNF grammar defined in Appendix A.
- **Operator Precedence**: Handled via stratified climbing functions:
  `assignment_expr` $\rightarrow$ `logical_or` $\rightarrow$ `logical_and` $\rightarrow$ `equality` $\rightarrow$ `relational` $\rightarrow$ `additive` $\rightarrow$ `multiplicative` $\rightarrow$ `unary` $\rightarrow$ `primary`.
- **Dangling Else**: Resolved by associating each `else` clause with the innermost open `if` statement.
- **Statement vs Declaration (`CM-SYN-004`)**: Bare, unbraced declarations are strictly rejected as statements.
- **Inspectable AST (`--dump-ast`)**: Implemented in `src/cminor/parser/ast_dump.py` providing human-readable, deterministic indented representations with exact source coordinates.

---

## 4. Semantic Analysis & Scopes (`src/cminor/sema/`)

- **Symbol Tables**: Hierarchical `Scope` chains. Each scope tracks local variable symbols, parameters, and parent links.
- **Shadowing & Redeclaration**: Declaring a variable in an inner block is permitted (shadowing), but declaring the same name twice within the same lexical scope raises `NAME_ERROR`.
- **Function Validation**:
  - Exactly one `int main(void)` definition is required.
  - Forward prototypes must strictly match later definitions in parameter count and types.
  - Undeclared function calls and unfulfilled forward prototypes raise `NAME_ERROR`.
- **Course Rule CM-STM-006**:
  The analyzer enforces that every `int`-returning function terminates with an explicit top-level return statement as its final block item.
- **Lvalue Checking**: Only identifiers (optionally parenthesized) can appear as the target of assignment operators.

---

## 5. Student Intermediate Representation (`src/cminor/ir/`)

- **Three-Address Code (TAC)**: Designed according to `CM-IR-001` - `CM-IR-004`, completely separate from backend IL.
- **Operands**: Distinct `Constant`, unique-scoped `Variable`, and sequential `Temporary` (`$t1`, `$t2`, ...).
- **Instructions**:
  - Arithmetic/Logic: `BinOpInstr`, `UnaryOpInstr`, `AssignInstr`
  - Control Flow: `LabelInstr`, `JumpInstr`, `BranchIfZeroInstr`, `BranchIfNotZeroInstr`
  - Calls/Returns: `ParamInstr`, `CallInstr`, `ReturnInstr`
- **Short-Circuit Evaluation**: Logical `&&` and `||` generate conditional jumps that skip the evaluation of right-hand operands when the left-hand side determines the outcome.

---

## 6. Backend Lowering & Integration (`src/cminor/codegen/`)

- **LLVM IR Lowering (`src/cminor/codegen/llvm_emitter.py`)**:
  - Generates valid LLVM textual IR for `x86_64-pc-linux-gnu`.
  - Uses abstract storage (`alloca`, `load`, `store`) for variables and parameters.
  - Normalizes boolean comparisons via `zext i1 to i32`.
- **QBE IL Lowering (`src/cminor/codegen/qbe_emitter.py`)**:
  - Generates valid QBE SSA textual IL for `amd64_sysv`.
  - Uses `alloc4 4`, `storew`, and `loadw` for local word variables.
- **External Invocation & Atomicity (`CM-CG-007`)**:
  - The driver invokes external backends (`llc` or `qbe`) with safe structured arguments (`CM-NFR-005`).
  - The generated assembly (`.s`) is created in a temporary file and atomically renamed (`os.replace`) upon zero exit status.

---

## 7. Diagnostics and Error Handling (`src/cminor/diagnostics.py`)

All errors follow a standardized format:
```text
<filepath>:<line>:<col>: error: [<DIAGNOSTIC_CODE>] <concise description>
<related_file>:<line>:<col>: note: <related declaration info>
```
Standard diagnostic categories include `LEXICAL_ERROR`, `SYNTAX_ERROR`, `NAME_ERROR`, `TYPE_ERROR`, `CALL_ERROR`, `RETURN_ERROR`, `CONTROL_FLOW_ERROR`, `UNSUPPORTED_FEATURE`, `UNSUPPORTED_PREPROCESSING_DIRECTIVE`, `UNSUPPORTED_LINE_SPLICING`, `IO_ERROR`, `BACKEND_ERROR`, `COMMAND_ERROR`, and `LIMIT_ERROR`.

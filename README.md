# C Minor Compiler (`cminorcc`)

A compliant, multi-stage compiler for the **C Minor** programming language targeting Linux x86-64 (System V AMD64 ABI), conforming to the *C Minor Compiler Software Requirements Specification Version 1.0*.

## Features

- **Lexical Analysis**: Full tokenization with precise 1-based source line and column tracking, rejection of preprocessing directives (`#`, `%:`) and line splicing (`\`).
- **Syntax Analysis**: Recursive descent parser building an inspectable Abstract Syntax Tree (AST) with source spans.
- **Semantic Analysis**: Multi-level symbol tables, scope resolution, type validation, loop control-flow validation, and function signature verification.
- **Student Intermediate Representation (IR)**: Inspectable Three-Address Code (TAC) preserving explicit control flow and short-circuit evaluation.
- **Backend Lowering**: Target code emission to LLVM IR (`.ll`) and QBE IL (`.ssa`), lowered to GNU-compatible x86-64 assembly (`.s`).
- **Comprehensive Driver**: Command-line interface `cminorcc` supporting `--check`, `--dump-tokens`, `--dump-ast`, `--dump-symbols`, `--dump-ir`, `--emit-backend-ir`, and `--capabilities`.

## Architecture

```
Source (.cm/.c)
      │
      ▼  [Lexer]
   Tokens  (--dump-tokens)
      │
      ▼  [Parser]
     AST   (--dump-ast)
      │
      ▼  [Semantic Analyzer]
 Decorated AST / Symbols (--dump-symbols, --check)
      │
      ▼  [IR Generator]
  Student IR (TAC) (--dump-ir)
      │
      ▼  [Backend Lowering]
 Backend IL (LLVM IR / QBE IL) (--emit-backend-ir)
      │
      ▼  [Native Backend]
 Assembly (.s)
```

## Project Structure

```text
complier-project/
├── bin/
│   ├── cminorcc             # Main executable wrapper (POSIX)
│   └── cminorcc.bat         # Windows executable wrapper
├── src/
│   └── cminor/
│       ├── __init__.py
│       ├── diagnostics.py   # Diagnostic codes and error reporter
│       ├── driver.py        # Driver orchestration and CLI options
│       ├── lexer/           # Lexer & token definitions
│       ├── parser/          # Parser & AST node definitions
│       ├── sema/            # Symbol tables & semantic validation
│       ├── ir/              # Student Three-Address Code IR
│       └── codegen/         # Lowering to LLVM IR / QBE IL
├── tests/                   # Unit, integration, acceptance & fuzz tests
└── docs/                    # Specifications and documentation
```

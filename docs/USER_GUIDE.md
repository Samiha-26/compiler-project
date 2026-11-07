# C Minor Compiler (`cminorcc`) — User Guide

This guide describes how to invoke and operate the `cminorcc` compiler, the accepted C Minor language grammar, supported command-line options, exit codes, and resource limits according to the *C Minor Compiler SRS Version 1.0*.

---

## 1. Quick Start

### Basic Compilation
To compile a C Minor source file (`.cm` or `.c`) into GNU-compatible x86-64 assembly (`.s`):
```bash
./bin/cminorcc sample.cm -o sample.s
```
If `-o` is omitted, the default output path is `<basename>.s`.

### On Windows
```cmd
bin\cminorcc.bat sample.cm -o sample.s
```

---

## 2. Driver Options

| Option | Description |
| :--- | :--- |
| `input.cm` | Input source file (must have extension `.cm` or `.c`). |
| `-o <path>` | Specify destination path for assembly (`.s`) or textual IR. |
| `--check` | Runs semantic analysis only without invoking the native backend. Exits 0 on success. |
| `--dump-tokens` | Prints all scanned tokens with 1-based source line and column numbers. |
| `--dump-ast` | Prints a deterministic, hierarchical representation of the Abstract Syntax Tree. |
| `--dump-symbols` | Prints the symbol table showing names, kinds, scopes, and source locations. |
| `--dump-ir` | Prints the student Three-Address Code (TAC) intermediate representation. |
| `--emit-backend-ir` | Generates backend IL (`.ll` for LLVM or `.ssa` for QBE) to stdout or `-o <path>`. |
| `--backend=<name>` | Selects the backend IL target: `llvm` (default) or `qbe`. |
| `--capabilities` | Displays compiler language version, target ABI, limits, and backend support. |
| `--version`, `-v` | Prints the compiler version and exits 0. |
| `--help`, `-h` | Displays command line usage information and exits 0. |

*Note*: Stage dump flags (`--dump-*`), `--check`, and `--emit-backend-ir` are mutually exclusive.

---

## 3. Exit Codes

- **`0`**: Successful execution of the requested compiler action.
- **`1`**: Source code error (lexical, syntax, semantic), file I/O failure, unsupported language construct, or backend tool failure.
- **`2`**: Command-line usage error (invalid options, missing arguments, mutually exclusive flags).

---

## 4. Language Specification & Exclusions

### Supported Language Profile
- **Types**: Signed 32-bit `int` only. The keyword `void` is valid only as a function return type or as `(void)` for an empty parameter list.
- **Variables**: Scalar local variables within blocks or `for` loop initializers. Inner-block shadowing is supported; redeclaration in the same scope is prohibited. Global variables are not allowed.
- **Functions**: Up to 6 parameters of type `int`. Exactly one `int main(void)` function definition is required. Every `int` function must end with an explicit top-level `return <expr>;`.
- **Operators**:
  - Arithmetic: `+`, `-`, `*`, `/`, `%`
  - Relational: `<`, `<=`, `>`, `>=`
  - Equality: `==`, `!=`
  - Logical: `&&`, `||` (with short-circuiting)
  - Unary: `+`, `-`, `!`
  - Assignment: `=` (right-associative)
- **Control Flow**: `if`/`else` (closest-matching `else`), `while`, `for (init; cond; update)` with `break` and `continue`.
- **Comments**: `//` single-line comments and `/* ... */` block comments.

### Exclusions & Rejections
- **Preprocessing Directives**: `#` or `%:` at the start of a line raises `UNSUPPORTED_PREPROCESSING_DIRECTIVE`.
- **Line Splicing**: Backslash immediately preceding a newline (`\` + `\n`) raises `UNSUPPORTED_LINE_SPLICING`.
- **Excluded Types**: `char`, `bool`, `float`, `double`, pointers, arrays, structs, unions, enums.
- **Excluded Operators**: `++`, `--`, compound assignments (`+=`, etc.), bitwise shifts (`<<`, `>>`), bitwise operators (`&`, `|`, `^`, `~`), ternary `?:`.

---

## 5. Implementation Limits

- Maximum input source size: 32 KiB (4,000 tokens)
- Maximum nesting level (blocks and expressions): 16 levels
- Maximum user-defined functions: 32 functions
- Maximum locals per block: 64 variables
- Maximum source line length: 2,048 characters

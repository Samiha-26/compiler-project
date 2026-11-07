# Requirements Traceability Ledger (`CM-VER-001`, `CM-DEL-005`)

This document records the traceability mapping between all compulsory and optional requirements defined in the *C Minor Compiler SRS 1.0*, their implementation components, and test evidence.

| Requirement ID | Description | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **CM-SCP-001** | Accept valid C Minor, reject unsupported source | `src/cminor/driver.py` | `tests/acceptance/` | Passed |
| **CM-SCP-002** | Personally implemented stages | `src/cminor/` | Architecture review | Passed |
| **CM-SCP-003** | Single .cm/.c input, no preprocessor | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-SCP-004** | Produce GNU-compatible assembly (.s) | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-SCP-005** | Teaching profile adherence | All modules | All test suites | Passed |
| **CM-SCP-006** | Trace source → tokens → AST → IR → IL → .s | `src/cminor/driver.py` | `test_appendix_b_positive.py` | Passed |
| **CM-LEX-001** | Identifiers, 1-based tracking, keywords | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_keywords_and_identifiers` | Passed |
| **CM-LEX-002** | Integer literals, rejection of 012/0x/floats | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_integer_literals` | Passed |
| **CM-LEX-003** | Comments and token boundary preservation | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_token_boundaries_across_block_comments` | Passed |
| **CM-LEX-004** | Longest-token operators & unsupported ops | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_unsupported_operators` | Passed |
| **CM-LEX-005** | Preprocessing directive rejection (#, %:) | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_preprocessing_directive_hash` | Passed |
| **CM-LEX-006** | Line-splicing rejection (\ + newline) | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_line_splicing_rejected` | Passed |
| **CM-LEX-007** | Controlled error on unknown characters | `src/cminor/lexer/scanner.py` | `test_lexer.py:test_unterminated_block_comment` | Passed |
| **CM-SYN-001** | Implement Appendix A grammar | `src/cminor/parser/parser.py` | `test_parser.py` | Passed |
| **CM-SYN-002** | Construct inspectable AST | `src/cminor/parser/ast.py` | `test_parser.py` | Passed |
| **CM-SYN-003** | Deterministic --dump-ast output | `src/cminor/parser/ast_dump.py` | Manual & CLI driver test | Passed |
| **CM-SYN-004** | Reject unbraced statements, dangling else | `src/cminor/parser/parser.py` | `test_parser.py:test_reject_bare_unbraced_declaration` | Passed |
| **CM-SEM-001** | Multi-level scopes and resolution | `src/cminor/sema/symbols.py` | `test_sema.py:test_shadowing_in_inner_block_is_allowed` | Passed |
| **CM-SEM-002** | Declaration before use, no duplicates | `src/cminor/sema/analyzer.py` | `test_sema.py:test_redeclaration_in_same_scope_raises_name_error` | Passed |
| **CM-SEM-003** | Modifiable int lvalue verification | `src/cminor/sema/analyzer.py` | `test_sema.py:test_assign_to_non_lvalue_raises_type_error` | Passed |
| **CM-SEM-004** | Function call, loop, and return checks | `src/cminor/sema/analyzer.py` | `test_sema.py:test_break_outside_loop_raises_control_flow_error` | Passed |
| **CM-SEM-005** | Halt before backend on errors | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-SEM-006** | Deterministic --dump-symbols output | `src/cminor/sema/analyzer.py` | Manual & driver test | Passed |
| **CM-EXP-001** | Decimal, calls, unary, binary, assign | `src/cminor/parser/parser.py` | `test_parser.py:test_precedence_arithmetic` | Passed |
| **CM-EXP-002** | Precedence & associativity rules | `src/cminor/parser/parser.py` | `test_parser.py:test_assignment_associativity` | Passed |
| **CM-EXP-003** | Expressions evaluate to int (0 or 1) | `src/cminor/ir/generator.py` | `test_ir.py:test_short_circuit_and_or` | Passed |
| **CM-EXP-005** | Short-circuiting for && and \|\| | `src/cminor/ir/generator.py` | `test_ir.py:test_short_circuit_and_or` | Passed |
| **CM-EXP-006** | Left-to-right evaluation sequencing | `src/cminor/ir/generator.py` | `test_ir.py:test_expression_tac` | Passed |
| **CM-STM-002** | For loop initializer scoping | `src/cminor/sema/analyzer.py` | `test_parser.py:test_for_loop_with_local_decl_init` | Passed |
| **CM-STM-003** | Break and continue semantics | `src/cminor/ir/generator.py` | `test_ir.py:test_loop_break_continue` | Passed |
| **CM-STM-004** | Exact int main(void) requirement | `src/cminor/sema/analyzer.py` | `test_sema.py:test_invalid_main_signature_raises_type_error` | Passed |
| **CM-STM-005** | Return type matching | `src/cminor/sema/analyzer.py` | `test_sema.py:test_void_function_returning_value_raises_return_error` | Passed |
| **CM-STM-006** | Explicit top-level final return check | `src/cminor/sema/analyzer.py` | `test_sema.py:test_missing_final_top_level_return_in_int_function` | Passed |
| **CM-IR-001** | Independent student Three-Address Code | `src/cminor/ir/instructions.py`| `test_ir.py` | Passed |
| **CM-IR-002** | TAC operands, operations, and labels | `src/cminor/ir/instructions.py`| `test_ir.py` | Passed |
| **CM-IR-003** | TAC explicit control flow preservation | `src/cminor/ir/generator.py` | `test_ir.py` | Passed |
| **CM-IR-004** | Deterministic --dump-ir output | `src/cminor/ir/instructions.py`| Manual & driver test | Passed |
| **CM-CG-001** | Textual LLVM IR (.ll) / QBE IL (.ssa) | `src/cminor/codegen/` | `test_codegen.py` | Passed |
| **CM-CG-002** | Abstract storage lowering (alloca/alloc4)| `src/cminor/codegen/` | `test_codegen.py` | Passed |
| **CM-CG-005** | Backend selection in driver | `src/cminor/driver.py` | `test_codegen.py` | Passed |
| **CM-CG-007** | Atomic .s replacement on success | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-CLI-001** | Runnable command cminorcc | `bin/cminorcc`, `bin/cminorcc.bat` | CLI execution tests | Passed |
| **CM-CLI-002** | Standard CLI options implementation | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-CLI-003** | Mutually exclusive stage dumps | `src/cminor/driver.py` | `test_driver.py:test_mutually_exclusive_flags_returns_2` | Passed |
| **CM-CLI-004** | --capabilities report | `src/cminor/driver.py` | `test_driver.py:test_capabilities_flag` | Passed |
| **CM-CLI-005** | Standardized exit codes (0, 1, 2) | `src/cminor/driver.py` | `test_driver.py` | Passed |
| **CM-DIA-001** | Stable diagnostic format with location | `src/cminor/diagnostics.py` | `test_lexer.py`, `test_sema.py` | Passed |
| **CM-DIA-002** | Standardized diagnostic codes | `src/cminor/diagnostics.py` | `test_appendix_b_negative.py` | Passed |
| **CM-NFR-003** | 100+ mutated robustness cases, 5s timeout | `tests/robustness/` | `test_robustness.py:test_100_mutated_inputs` | Passed |
| **CM-NFR-005** | Structured subprocess invocation | `src/cminor/driver.py` | Code inspection | Passed |

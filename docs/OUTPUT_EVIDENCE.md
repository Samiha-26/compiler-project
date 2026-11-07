# Output Evidence Report (`CM-DEL-004`, `CM-SCP-006`)

This document demonstrates the full compilation trace of the C Minor compiler from source code through tokens, Abstract Syntax Tree (AST), symbol tables, student Three-Address Code (TAC), backend intermediate representations (LLVM IR and QBE IL), and representative failure diagnostics.

---

## 1. Trace Sample Program

The sample program demonstrates both a loop (`for`) and a recursive function call (`fact`), satisfying requirement `CM-SCP-006`:

```c
int fact(int n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}

int main(void) {
    int sum = 0;
    for (int i = 1; i <= 4; i = i + 1) {
        sum = sum + fact(i);
    }
    if (sum != 33) return 1;
    return 0;
}
```

---

## 2. Stage 1: Lexical Analysis (`--dump-tokens`)

Command:
```bash
./bin/cminorcc --dump-tokens tests/fixtures/trace_sample.cm
```

Output:
```text
1:1        KW_INT          'int'
1:5        IDENTIFIER      'fact'
1:9        LPAREN          '('
1:10       KW_INT          'int'
1:14       IDENTIFIER      'n'
1:15       RPAREN          ')'
1:17       LBRACE          '{'
2:5        KW_IF           'if'
2:8        LPAREN          '('
2:9        IDENTIFIER      'n'
2:11       LESS_EQUAL      '<='
2:14       INT_LITERAL     '1' (value=1)
2:15       RPAREN          ')'
2:17       KW_RETURN       'return'
2:24       INT_LITERAL     '1' (value=1)
2:25       SEMICOLON       ';'
3:5        KW_RETURN       'return'
3:12       IDENTIFIER      'n'
3:14       STAR            '*'
3:16       IDENTIFIER      'fact'
3:20       LPAREN          '('
3:21       IDENTIFIER      'n'
3:23       MINUS           '-'
3:25       INT_LITERAL     '1' (value=1)
3:26       RPAREN          ')'
3:27       SEMICOLON       ';'
4:1        RBRACE          '}'
6:1        KW_INT          'int'
6:5        IDENTIFIER      'main'
6:9        LPAREN          '('
6:10       KW_VOID         'void'
6:14       RPAREN          ')'
6:16       LBRACE          '{'
7:5        KW_INT          'int'
7:9        IDENTIFIER      'sum'
7:13       ASSIGN          '='
7:15       INT_LITERAL     '0' (value=0)
7:16       SEMICOLON       ';'
8:5        KW_FOR          'for'
8:9        LPAREN          '('
8:10       KW_INT          'int'
8:14       IDENTIFIER      'i'
8:16       ASSIGN          '='
8:18       INT_LITERAL     '1' (value=1)
8:19       SEMICOLON       ';'
8:21       IDENTIFIER      'i'
8:23       LESS_EQUAL      '<='
8:26       INT_LITERAL     '4' (value=4)
8:27       SEMICOLON       ';'
8:29       IDENTIFIER      'i'
8:31       ASSIGN          '='
8:33       IDENTIFIER      'i'
8:35       PLUS            '+'
8:37       INT_LITERAL     '1' (value=1)
8:38       RPAREN          ')'
8:40       LBRACE          '{'
9:9        IDENTIFIER      'sum'
9:13       ASSIGN          '='
9:15       IDENTIFIER      'sum'
9:19       PLUS            '+'
9:21       IDENTIFIER      'fact'
9:25       LPAREN          '('
9:26       IDENTIFIER      'i'
9:27       RPAREN          ')'
9:28       SEMICOLON       ';'
10:5       RBRACE          '}'
11:5       KW_IF           'if'
11:8       LPAREN          '('
11:9       IDENTIFIER      'sum'
11:13      BANG_EQUAL      '!='
11:16      INT_LITERAL     '33' (value=33)
11:18      RPAREN          ')'
11:20      KW_RETURN       'return'
11:27      INT_LITERAL     '1' (value=1)
11:28      SEMICOLON       ';'
12:5       KW_RETURN       'return'
12:12      INT_LITERAL     '0' (value=0)
12:13      SEMICOLON       ';'
13:1       RBRACE          '}'
14:1       EOF
```

---

## 3. Stage 2: Abstract Syntax Tree (`--dump-ast`)

Command:
```bash
./bin/cminorcc --dump-ast tests/fixtures/trace_sample.cm
```

Output:
```text
Program <1:1>
  FunctionDef <1:1>: int fact(int n)
    Block <1:17>
      IfStmt <2:5>
        Condition:
          BinaryExpr <2:9> (<=)
            VarExpr <2:9>: n
            IntLiteral <2:14>: 1
        Then:
          ReturnStmt <2:17>
            IntLiteral <2:24>: 1
      ReturnStmt <3:5>
        BinaryExpr <3:12> (*)
          VarExpr <3:12>: n
          CallExpr <3:16>: fact()
            BinaryExpr <3:21> (-)
              VarExpr <3:21>: n
              IntLiteral <3:25>: 1
  FunctionDef <6:1>: int main(void)
    Block <6:16>
      VarDecl <7:5>: int sum =
        IntLiteral <7:15>: 0
      ForStmt <8:5>
        Init:
          VarDecl <8:10>: int i =
            IntLiteral <8:18>: 1
        Condition:
          BinaryExpr <8:21> (<=)
            VarExpr <8:21>: i
            IntLiteral <8:26>: 4
        Update:
          AssignExpr <8:29> (=)
            VarExpr <8:29>: i
            BinaryExpr <8:33> (+)
              VarExpr <8:33>: i
              IntLiteral <8:37>: 1
        Body:
          Block <8:40>
            ExprStmt <9:9>
              AssignExpr <9:9> (=)
                VarExpr <9:9>: sum
                BinaryExpr <9:15> (+)
                  VarExpr <9:15>: sum
                  CallExpr <9:21>: fact()
                    VarExpr <9:26>: i
      IfStmt <11:5>
        Condition:
          BinaryExpr <11:9> (!=)
            VarExpr <11:9>: sum
            IntLiteral <11:16>: 33
        Then:
          ReturnStmt <11:20>
            IntLiteral <11:27>: 1
      ReturnStmt <12:5>
        IntLiteral <12:12>: 0
```

---

## 4. Stage 3: Symbol Table & Scopes (`--dump-symbols`)

Command:
```bash
./bin/cminorcc --dump-symbols tests/fixtures/trace_sample.cm
```

Output:
```text
================================ Symbol Table ================================
Name             Kind         Type/Sig           Scope                    Location
------------------------------------------------------------------------------
fact             function     int (int)          scope=global(depth=0)    loc=<1:1> [defined]
n                parameter    int                scope=fn_fact_1(depth=1) loc=<1:14>
main             function     int (void)         scope=global(depth=0)    loc=<6:1> [defined]
sum              variable     int                scope=fn_main_2(depth=1) loc=<7:5>
i                variable     int                scope=for_3(depth=2)     loc=<8:10>
```

---

## 5. Stage 4: Student Three-Address Code IR (`--dump-ir`)

Command:
```bash
./bin/cminorcc --dump-ir tests/fixtures/trace_sample.cm
```

Output:
```text
function int @fact(%n_1):
    $t1 = %n_1 <= $1
    br_zero $t1, .L_endif1
    return $1
.L_endif1:
    $t2 = %n_1 - $1
    param $t2
    $t3 = call @fact(1)
    $t4 = %n_1 * $t3
    return $t4

function int @main():
    %sum_2 = $0
    %i_3 = $1
.L_for_cond1:
    $t5 = %i_3 <= $4
    br_zero $t5, .L_for_end1
.L_for_body1:
    param %i_3
    $t6 = call @fact(1)
    $t7 = %sum_2 + $t6
    %sum_2 = $t7
.L_for_update1:
    $t8 = %i_3 + $1
    %i_3 = $t8
    jump .L_for_cond1
.L_for_end1:
    $t9 = %sum_2 != $33
    br_zero $t9, .L_endif2
    return $1
.L_endif2:
    return $0
```

---

## 6. Stage 5: Emitted Backend Intermediate Representation

### LLVM IR (`--emit-backend-ir --backend=llvm`)
```llvm
; ModuleID = "cminor"
source_filename = "cminor"
target triple = "x86_64-pc-linux-gnu"

define i32 @fact(i32 %arg_0) {
entry:
    %ptr_n_1 = alloca i32, align 4
    store i32 %arg_0, ptr %ptr_n_1, align 4
    %r1 = load i32, ptr %ptr_n_1, align 4
    %r3 = icmp sle i32 %r1, 1
    %r2 = zext i1 %r3 to i32
    %r4 = icmp eq i32 %r2, 0
    br i1 %r4, label %L_endif1, label %r5
r5:
    ret i32 1
L_endif1:
    %r6 = load i32, ptr %ptr_n_1, align 4
    %r7 = sub nsw i32 %r6, 1
    %r8 = call i32 @fact(i32 %r7)
    %r9 = load i32, ptr %ptr_n_1, align 4
    %r10 = mul nsw i32 %r9, %r8
    ret i32 %r10
}

define i32 @main() {
entry:
    %ptr_sum_2 = alloca i32, align 4
    store i32 0, ptr %ptr_sum_2, align 4
    %ptr_i_3 = alloca i32, align 4
    store i32 0, ptr %ptr_i_3, align 4
    store i32 0, ptr %ptr_sum_2, align 4
    store i32 1, ptr %ptr_i_3, align 4
    br label %L_for_cond1
L_for_cond1:
    %r1 = load i32, ptr %ptr_i_3, align 4
    %r3 = icmp sle i32 %r1, 4
    %r2 = zext i1 %r3 to i32
    %r4 = icmp eq i32 %r2, 0
    br i1 %r4, label %L_for_end1, label %r5
r5:
    br label %L_for_body1
L_for_body1:
    %r6 = load i32, ptr %ptr_i_3, align 4
    %r7 = call i32 @fact(i32 %r6)
    %r8 = load i32, ptr %ptr_sum_2, align 4
    %r9 = add nsw i32 %r8, %r7
    store i32 %r9, ptr %ptr_sum_2, align 4
    br label %L_for_update1
L_for_update1:
    %r10 = load i32, ptr %ptr_i_3, align 4
    %r11 = add nsw i32 %r10, 1
    store i32 %r11, ptr %ptr_i_3, align 4
    br label %L_for_cond1
L_for_end1:
    %r12 = load i32, ptr %ptr_sum_2, align 4
    %r14 = icmp ne i32 %r12, 33
    %r13 = zext i1 %r14 to i32
    %r15 = icmp eq i32 %r13, 0
    br i1 %r15, label %L_endif2, label %r16
r16:
    ret i32 1
L_endif2:
    ret i32 0
}
```

### QBE IL (`--emit-backend-ir --backend=qbe`)
```qbe
export function w $fact(w %arg_0) {
@start
    %ptr_n_1 =l alloc4 4
    storew %arg_0, %ptr_n_1
    %q1 =w loadw %ptr_n_1
    %q2 =w cslew %q1, 1
    jnz %q2, @L_endif1, @q3
@q3
    ret 1
@L_endif1
    %q4 =w loadw %ptr_n_1
    %q5 =w sub %q4, 1
    %q6 =w call $fact(w %q5)
    %q7 =w loadw %ptr_n_1
    %q8 =w mul %q7, %q6
    ret %q8
}

export function w $main() {
@start
    %ptr_sum_2 =l alloc4 4
    storew 0, %ptr_sum_2
    %ptr_i_3 =l alloc4 4
    storew 0, %ptr_i_3
    storew 0, %ptr_sum_2
    storew 1, %ptr_i_3
    jmp @L_for_cond1
@L_for_cond1
    %q1 =w loadw %ptr_i_3
    %q2 =w cslew %q1, 4
    jnz %q2, @L_for_end1, @q3
@q3
    jmp @L_for_body1
@L_for_body1
    %q4 =w loadw %ptr_i_3
    %q5 =w call $fact(w %q4)
    %q6 =w loadw %ptr_sum_2
    %q7 =w add %q6, %q5
    storew %q7, %ptr_sum_2
    jmp @L_for_update1
@L_for_update1
    %q8 =w loadw %ptr_i_3
    %q9 =w add %q8, 1
    storew %q9, %ptr_i_3
    jmp @L_for_cond1
@L_for_end1
    %q10 =w loadw %ptr_sum_2
    %q11 =w cnew %q10, 33
    jnz %q11, @L_endif2, @q12
@q12
    ret 1
@L_endif2
    ret 0
}
```

---

## 7. Representative Failure Diagnostics

### 1. Preprocessing Directive Rejection (`CM-LEX-005`)
Input: `#include <stdio.h>`
```text
test.cm:1:1: error: [UNSUPPORTED_PREPROCESSING_DIRECTIVE] Preprocessing directive '#' is not supported.
```

### 2. Line Splicing Rejection (`CM-LEX-006`)
Input: `int x = \\\n 10;`
```text
test.cm:1:9: error: [UNSUPPORTED_LINE_SPLICING] Source line splicing with backslash-newline is not supported.
```

### 3. Syntax Error — Bare Declaration (`CM-SYN-004`)
Input: `if (1) int x = 0;`
```text
test.cm:1:8: error: [SYNTAX_ERROR] A declaration cannot appear as a bare statement. Use a block '{ ... }'.
```

### 4. Semantic Name Error — Duplicate Identifier (`CM-LANG-004`)
Input: `int x = 5; int x = 6;` in same block
```text
test.cm:1:16: error: [NAME_ERROR] Redeclaration of variable 'x' in the same scope.
test.cm:1:5: note: Previous declaration was here.
```

### 5. Semantic Return Error — Missing Top-level Final Return (`CM-STM-006`)
Input: `int main(void) { if (1) return 0; }`
```text
test.cm:1:35: error: [RETURN_ERROR] Function 'main' missing explicit top-level final return statement.
```

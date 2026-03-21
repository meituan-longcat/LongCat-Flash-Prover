# lean4parser

A lightweight Lean 4 parser designed for proof legality detection.

## Overview

`lean4parser` provides a full parser for Lean 4 code, including lexical analysis, syntactic analysis (AST generation), and source code reconstruction. The checker module is specifically designed for **legality detection** to identify potential cheating risks in proofs, such as:

- Modified or added meta/syntax components
- Changed global variable declarations
- Illegal kind transitions (e.g., `def` -> `theorem`)
- Signature tampering in prerequisite definitions
- New axiom/opaque definitions
- Blacklisted `set_option` usage
- Redefinition of built-in identifiers

## Usage

### Parse Lean 4 Code

```python
from lean4parser import parse

formal_statement = r"""
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

/-- If $3a + b + c = -3, a+3b+c = 9, a+b+3c = 19$, then find $abc$. Show that it is -56.-/
theorem mathd_algebra_338 (a b c : ℝ) (h₀ : 3 * a + b + c = -3) (h₁ : a + 3 * b + c = 9)
    (h₂ : a + b + 3 * c = 19) : a * b * c = -56 := by sorry
""".strip()

ast = parse(formal_statement)
print(ast.to_tree())
```

Output:
```
Module
└── body
    ├── Import
    │   ├── module: 'Mathlib'
    │   └── runtime: False
    ├── Import
    │   ├── module: 'Aesop'
    │   └── runtime: False
    ├── SetOption
    │   ├── name: 'maxHeartbeats'
    │   └── value: 0
    ├── Open
    │   ├── namespaces
    │   │   ├── 'BigOperators'
    │   │   ├── 'Real'
    │   │   ├── 'Nat'
    │   │   ├── 'Topology'
    │   │   └── 'Rat'
    │   ├── abbrev: False
    │   └── is_scoped: False
    └── Definition
        ├── has_at: False
        ├── kind: 'theorem'
        ├── name: 'mathd_algebra_338'
        ├── binders
        │   ├── Binder
        │   │   ├── names
        │   │   │   ├── 'a'
        │   │   │   ├── 'b'
        │   │   │   └── 'c'
        │   │   ├── type:
        │   │   │   └── RawExpr
        │   │   │       └── content: ' ℝ'
        │   │   ├── is_implicit: False
        │   │   ├── is_strict_implicit: False
        │   │   ├── is_inst_implicit: False
        │   │   └── has_parens: True
        │   ├── Binder
        │   │   ├── names
        │   │   │   └── 'h₀'
        │   │   ├── type:
        │   │   │   └── RawExpr
        │   │   │       └── content: ' 3 * a + b + c = -3'
        │   │   ├── is_implicit: False
        │   │   ├── is_strict_implicit: False
        │   │   ├── is_inst_implicit: False
        │   │   └── has_parens: True
        │   ├── Binder
        │   │   ├── names
        │   │   │   └── 'h₁'
        │   │   ├── type:
        │   │   │   └── RawExpr
        │   │   │       └── content: ' a + 3 * b + c = 9'
        │   │   ├── is_implicit: False
        │   │   ├── is_strict_implicit: False
        │   │   ├── is_inst_implicit: False
        │   │   └── has_parens: True
        │   └── Binder
        │       ├── names
        │       │   └── 'h₂'
        │       ├── type:
        │       │   └── RawExpr
        │       │       └── content: ' a + b + 3 * c = 19'
        │       ├── is_implicit: False
        │       ├── is_strict_implicit: False
        │       ├── is_inst_implicit: False
        │       └── has_parens: True
        ├── type:
        │   └── RawExpr
        │       └── content: ' a * b * c = -56'
        ├── body:
        │   └── RawExpr
        │       └── content: ' by sorry'
        └── has_coloneq: True
```

### Legality Detection via AST Checking

```python
from lean4parser import check_consistency

formal_statement = r"""
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

/-- If $3a + b + c = -3, a+3b+c = 9, a+b+3c = 19$, then find $abc$. Show that it is -56.-/
theorem mathd_algebra_338 (a b c : ℝ) (h₀ : 3 * a + b + c = -3) (h₁ : a + 3 * b + c = 9)
    (h₂ : a + b + 3 * c = 19) : a * b * c = -56 := by sorry
""".strip()

proof = r"""
import Mathlib
open Real

/--
Given real numbers a, b, c satisfying the three linear equations,
the sum a + b + c equals 5.
-/
lemma sum_eq_five (a b c : ℝ) (h1 : 3 * a + b + c = -3) (h2 : a + 3 * b + c = 9) (h3 : a + b + 3 * c = 19) : a + b + c = 5 := by
  have h : 5 * (a + b + c) = 25 := by
    linarith
  linarith

/--
Given that a + b + c = 5 and 3*a + b + c = -3, we can deduce a = -4.
-/
lemma a_eq_neg_four (a b c : ℝ) (h_sum : a + b + c = 5) (h1 : 3 * a + b + c = -3) : a = -4 := by
  linarith

/--
Given that a + b + c = 5 and a + 3*b + c = 9, we can deduce b = 2.
-/
lemma b_eq_two (a b c : ℝ) (h_sum : a + b + c = 5) (h2 : a + 3 * b + c = 9) : b = 2 := by
  linarith

/--
Given that a + b + c = 5 and a + b + 3*c = 19, we can deduce c = 7.
-/
lemma c_eq_seven (a b c : ℝ) (h_sum : a + b + c = 5) (h3 : a + b + 3 * c = 19) : c = 7 := by
  linarith

/--
Given a = -4, b = 2, c = 7, the product a * b * c equals -56.
-/
lemma product_eq_neg_fifty_six (a b c : ℝ) (ha : a = -4) (hb : b = 2) (hc : c = 7) : a * b * c = -56 := by
  rw [ha, hb, hc]
  norm_num

theorem mathd_algebra_338 (a b c : ℝ) (h₀ : 3 * a + b + c = -3) (h₁ : a + 3 * b + c = 9) (h₂ : a + b + 3 * c = 19) : a * b * c = -56 := by
  have h_sum := sum_eq_five a b c h₀ h₁ h₂
  have ha : a = -4 := a_eq_neg_four a b c h_sum h₀
  have hb : b = 2 := b_eq_two a b c h_sum h₁
  have hc : c = 7 := c_eq_seven a b c h_sum h₂
  exact product_eq_neg_fifty_six a b c ha hb hc
""".strip()

is_valid, reason = check_consistency(formal_statement, proof)
print(f"Valid: {is_valid}, Reason: {reason}")
```

## Contributing

If you encounter any issues or have suggestions, please feel free to open an issue.


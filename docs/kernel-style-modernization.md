# Kernel style modernization

This branch is a non-semantic modernization of `holpy/kernel`: module and API
documentation, NumPy-style docstrings, `from __future__ import annotations`,
and type annotations. No derivation rule, substitution algorithm, identifier
arithmetic, or proof-checking branch was changed.

## File-by-file

- `kernel/__init__.py`
  - Added a module docstring describing the trusted core.
- `kernel/type.py`
  - Module docstring and deferred annotations.
  - Typed exception constructors, `TyInst`, `Type`, `STVar`, `TVar`, `TConst`,
    and `TFun`.
  - NumPy-style documentation for `subst`, `match_incr`, `match`, and
    `strip_type`; added missing docs for `convert_stvar` and
    `is_numeral_type`.
  - Removed an unused `term_ord` import.
- `kernel/term.py`
  - Module docstring; the file already used deferred annotations.
  - Declared the union-of-constructors attributes (`T`, `name`, `fun`, `arg`,
    `var_name`, `var_T`, `body`, `n`, `_id`, `_hash_val`) on `Term` for type
    checkers. The constructors still set exactly the same runtime attributes.
  - Typed and documented the public predicates, substitution operations,
    arithmetic operators, term constructors, and numeral helpers.
  - Corrected the `occurs_var` return annotation from `Term` to `bool`; the
    implementation already returned a boolean.
- `kernel/thm.py`
  - Module docstring and deferred annotations.
  - Typed `Thm` and every primitive derivation rule; added NumPy-style
    parameter/return documentation for each rule.
  - Corrected the `assums` annotation to `list[Term]`; the implementation
    already returned the antecedent list.
- `kernel/proof.py`
  - Module docstring and deferred annotations.
  - Typed `ItemID`, `ProofItem`, and `Proof`; documented identifier arithmetic
    and subproof navigation.
  - Corrected `ItemID.can_depend_on` to return `bool`.
  - `Proof.add_item` now defaults `prevs` to `None` and creates a fresh list
    internally. The old `[]` default was never mutated, so behavior is
    unchanged; this removes a shared-mutable-default hazard.
- `kernel/proofterm.py`
  - Module docstring; typed the proof-term API, conversions, export, and tactic
    application. No branch logic changed.
- `kernel/theory.py`
  - Module docstring and deferred annotations.
  - Typed `Theory`, proof checking, extension application, and the global
    theory/macro registry.
  - `EmptyTheory` intentionally remains local-only: it returns a new theory
    without mutating the global `thy`, matching the original behavior.
  - `get_proof_rule_sig("variable")` still returns `typing.Tuple[str, Type]`.
- `kernel/extension.py`
  - Module docstring and deferred annotations.
  - Typed all five extension kinds. `Proof` is imported under `TYPE_CHECKING`
    only, so no new runtime import cycle is introduced.
- `kernel/macro.py`
  - Module docstring and deferred annotations.
  - Typed the macro interface. `limit` is a class-level annotation only; it is
    not initialized in `__init__`, preserving the original `AttributeError`
    behavior for macros that do not set it.
- `kernel/report.py`
  - Module docstring; typed report fields and methods.
- `kernel/term_ord.py`
  - Module docstring; typed comparators and documented the ordering used by
    `sorted_typs`/`sorted_terms`. No comparison logic changed.

## Behavior-adjacent summary

- `Proof.add_item`: default `prevs` changed from `[]` to `None`; no observable
  behavior change for callers.
- `Thm.assums`, `Term.occurs_var`, and `ItemID.can_depend_on`: annotations
  corrected to match their existing return values.
- `Term` and `Macro`: class-level annotations added for type checkers; no
  runtime attributes were added.

## Verification

```text
kernel tests: 119 passed
full suite:   13 failures, 60 errors (pre-existing integral / Python 3.13
              cgi+msilib issues; no kernel failures)
kernel LSP:   0 error diagnostics
```

The full-suite failures are unchanged in kind from the pre-modernization
baseline; the error count is lower because unrelated stale diagnostics were
cleared during the branch work.

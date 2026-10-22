# Logic style modernization

This branch modernizes `holpy/logic`: module and API documentation, NumPy-style
docstrings, deferred annotations, and public type annotations. The logic
algorithms and proof construction are unchanged except where noted below.

## File-by-file

- `logic/__init__.py`
  - Added a package docstring.
- `logic/context.py`
  - Module docstring and deferred annotations.
  - Typed `Context`, `fresh_context`, and `set_context`; documented context
    construction and the temporary-context context manager.
- `logic/matcher.py`
  - Deferred annotations; typed `MatchException` and all matching entry points;
    added a docstring to `find_term`.
- `logic/basic.py`
  - Module docstring and deferred annotations.
  - Removed unused imports (`term`, `Var`, `Theory`, `Thm`, `extension`) and an
    unused `timestamp` assignment in `load_metadata`.
  - Preserved the intentional side-effect imports that register macros and
    methods (`z3wrapper`, `data.expr`, `data.real`, `imperative.imp`) and
    marked them with `# noqa: F401`.
- `logic/auto.py`
  - Module docstring and deferred annotations.
  - Typed the automation registry, solve/normalize entry points, macro, and
    conversion.
  - Replaced diagnostic `print` calls with `logging` (`debug_auto` at DEBUG,
    the macro mismatch path at ERROR). No search or normalization logic changed.
- `logic/conv.py`
  - Module docstring and deferred annotations.
  - Documented every conversion class and `get_proof_term` implementation.
  - Annotated the `rewr_conv` cache fields and added type-narrowing asserts in
    `get_proof_term`; the rewrite algorithm is unchanged.
  - Replaced one assertion message with an f-string to avoid the pi-lens
    `no-assert-tuple` false positive on a formatted message tuple.
  - Removed unused `Proof`, `TyInst`, `Var`, and `Bound` imports.
- `logic/tactic.py`
  - Module docstring and deferred annotations.
  - Documented all tactic classes and `get_proof_term` methods.
  - Added type guards in `var_induct` and `intros`; removed an unused
    `As = goal.hyps` assignment in `cases`; used an f-string for the
    `inst_exists_goal` type-mismatch message. No tactic behavior changed.
- `logic/logic.py`
  - Module docstring and deferred annotations.
  - Documented the remaining public helpers and macro classes; added generic
    `get_proof_term`/`eval` documentation where the class docstring carries the
    algorithm description.
  - Removed unused `TVar`, `TyInst`, `Abs`, `top_conv`, and `beta_conv`
    imports; imported `Type` for the `if_t` annotation.

## Behavior-adjacent summary

- `auto.py` diagnostic output moves from `print` to `logging`.
- `basic.py` no longer performs an unused `getmtime` call in `load_metadata`.
- `conv.py`/`tactic.py` gained type-narrowing assertions and f-string
  assertion messages; the guarded conditions already had to hold.
- No matching, conversion, normalization, tactic, or macro derivation logic was
  changed.

## Verification

```text
logic tests: 95 passed
full suite:  13 failures, 60 errors (pre-existing integral / Python 3.13
             cgi+msilib issues; no logic failures)
logic LSP:   0 error diagnostics
```

This branch is stacked on `style/kernel`; the intended PR base is
`style/kernel` until that PR merges. The logic-only diff is `holpy/logic`.

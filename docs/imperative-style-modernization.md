# Imperative style modernization

This branch modernizes `holpy/imperative`: module/API documentation, deferred
annotations, and a cleanup of the expression/parser surfaces. It also fixes
two pre-existing expression conversion bugs found by the type checker.

## File-by-file

- `imperative/__init__.py`
  - Added a package docstring.
- `imperative/com.py`
  - Deferred annotations and command-node documentation; removed unused
    `Term`, `Var`, and `logic` imports.
- `imperative/expr.py`
  - Deferred annotations and documentation for the expression hierarchy.
  - Fixed `ArrayElt.convert_hol` and `Field.convert_hol`, which called
    `convert_hol` as a free function instead of a method.
  - Fixed `ArrayElt`/`Field` to call the imported `nth`/`length` helpers
    instead of `list.nth`/`list.length` (the builtin has no such methods).
  - Removed the `true` import shadowed by the module-level `true` constant.
- `imperative/imp.py`
  - Deferred annotations and documentation for commands, semantics,
    Hoare triples, macros, and methods; no logic changed.
- `imperative/parser.py`, `imperative/parser2.py`
  - Deferred annotations, transformer/production documentation, and import
    cleanup; parsing behavior unchanged.

## Behavior-adjacent summary

- The two expression conversion fixes change the failure mode from
  `NameError`/`AttributeError` to the intended HOL conversion.
- No command, semantics, VCG, macro, or parser algorithm was changed.

## Verification

```text
imperative tests: 18 passed
```

This branch is stacked on `style/kernel`; the intended PR base is
`style/kernel` until that PR merges.

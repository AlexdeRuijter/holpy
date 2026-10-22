# Utility style modernization

This branch modernizes `holpy/util`: module documentation, deferred
annotations, public typing, and docstrings for the name, runtime-typecheck,
union-find, and polynomial helpers.

## File-by-file

- `util/__init__.py`
  - Added a package docstring.
- `util/name.py`
  - Deferred annotations and typed signatures for `get_variant_name` and
    `get_variant_names`; behavior unchanged.
- `util/typecheck.py`
  - Deferred annotations and a complete NumPy-style docstring for
    `checkinstance`; behavior unchanged.
- `util/unionfind.py`
  - Deferred annotations; typed `parents` and `size`, all public methods, and
    documented the union-by-size policy; behavior unchanged.
- `util/poly.py`
  - Deferred annotations and typed `Monomial`/`Polynomial` APIs and helpers.
  - Added docstrings for the monomial/polynomial operations.
  - `Monomial.__le__` now returns a real `bool` instead of the integer from
    `compare_atom`; the boolean result is identical and `__lt__` relies only on
    truthiness. This is the only behavior-adjacent change.

## Verification

```text
util tests: 2 passed
util LSP:   0 error diagnostics
```

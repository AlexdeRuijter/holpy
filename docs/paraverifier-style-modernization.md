# Paraverifier style modernization

This branch modernizes `holpy/paraverifier`: module/API documentation, deferred
annotations, and public typing for the GCL bridge and parametrized-system
loader. Verification logic is unchanged.

## File-by-file

- `paraverifier/__init__.py`
  - Added a package docstring.
- `paraverifier/gcl.py`
  - Deferred annotations; typed `convert_term` and `mk_assign`.
  - Removed an unused `holpy.logic.logic` import; no logic changed.
- `paraverifier/paraverifier.py`
  - Module docstring and deferred annotations.
  - Typed the `ParaSystem` constructor and fields, state replacement, subgoal
    construction/verification hints, and the JSON/hint loaders.
  - Added docstrings for `convert_hint_type`, the proof skeleton, and both
    loaders.
  - Removed the unused `printer` import; the commented debug prints are left
    untouched.
  - Marked the intentionally-built-but-unused proof-skeleton locals in
    `get_proof` with `# noqa: F841`; they are retained because constructing the
    proof terms is part of the existing (incomplete) skeleton behavior.

## Verification

```text
paraverifier tests: 4 passed
paraverifier LSP:   0 error diagnostics
```

The automated cross-module cascade on this branch refers to `util/` and
`logic/` files that are fixed on `style/util` and `style/logic`; this branch
does not modify them.

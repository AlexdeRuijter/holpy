# Geometry style modernization

This branch modernizes `holpy/geometry`: module/API documentation, deferred
annotations, and public typing for facts, lines, circles, rules, the prover,
and the geometry parser. Prover/search logic is unchanged.

## File-by-file

- `geometry/__init__.py`
  - Added a package docstring.
- `geometry/expr.py`
  - Deferred annotations; documented `Fact`, `Line`, `Circle`, `Rule`, and
    `Prover`, including the hash/equality/string surface and prover helpers.
  - Added constructor/method annotations for the geometry datatypes.
  - Corrected `get_applicable_facts` to return `List[List[Fact]]` (it already
    builds lists of fact tuples); this is the only annotation correction with
    type-checking significance.
  - Corrected `Circle.combine` and `Line.combine` to return `None` and mutate in place.
  - Removed unused `pstats`/`cProfile` imports and three unused
    `can_combine = False` locals; split the combined `itertools, copy` import.
- `geometry/parser.py`
  - Deferred annotations; documented the transformer and every parse helper;
    typed the transformer methods. Removed an unused `lark.exceptions` import.
- `geometry/ruleset.py`
  - Deferred annotations; removed an unused `Fact`/`Rule` import.

## Verification

```text
geometry tests: 25 passed
geometry LSP:   0 error diagnostics
```

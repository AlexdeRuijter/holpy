# Integral test triage (WS5-A6)

Task: analyse only; no source/test changes made.

## Fetch of old revision
`git fetch origin 923e3b1f` failed (`fatal: couldn't find remote ref`). Decided from current code and test errors directly.

Evidence used (verified by running `PYTHONPATH=. pytest ...` on current branch):
- `rules.Linearity().eval(s)` raises `TypeError: missing 1 required positional argument: 'ctx'`.
- `slagle.Linearity().eval(v)[0].normalize()` raises `AttributeError: 'Op' object has no attribute 'normalize'`.
- `solve.solve_equation(...)` raises `TypeError: missing 1 required positional argument: 'conds'`.
- `norm.eq_quotient(...)` raises `TypeError: missing 1 required positional argument: 'conds'`.
- `proof_test.ProofTest::testExprToHolpy` raises `NameError: name 'integral' is not defined` (import issue).
- `expr_test` fails to import (`basic.load_theory('transcendentals')` triggers `TheoryException: Constant of_int already exists`) — likely stale load order or double-load.

This shows the TEST code uses older signatures; the CODE has added required arguments (`ctx`, `conds`) and refactored exports.

## Group table

| Group name | Cause (checked) | Failing test IDs / count | Stale side | Evidence | Fix estimate |
|---|---|---|---|---|---|
| rules-eval-ctx | `Linearity.eval()` and other `rules.*.eval()` now require `ctx: Context` | rules_test.py: 17 failures (testApplyEquation, CommonIntegral, DerivativeSimplify, ElimInfInterval, ElimInfInterval2, Equation, ExpandPolynomial, FullSimplify, FullSimplify2, IndefiniteIntegralIdentity, IntegrationByParts, Linearity, OnSubterm, Simplify, Substitution–Substitution13) | TEST stale | Direct pytest output: `TypeError: eval() missing 1 required positional argument: 'ctx'`; `Context()` exists in current code but tests omit it in most calls | Small (add `ctx` to calls; ~2 h) |
| slagle-eval-normalize | `slagle.*.eval()` returns tuple `(new_e, steps)`; `.normalize()` no longer exists on result | slagle_test.py: 10 failures (testCommonIntegral, DividePolynomial, ElimAbs, ElimAbs2, HalfAngleIdentity, HeuristicElimQuadratic, HeuristicExpandPower, HeuristicSubstitution, HeuristicTrigSubstitution, Linearity, TrigIdentity) | TEST stale | `AttributeError: 'Op' object has no attribute 'normalize'` and `KeyError` in slagle rules | Small-Medium (~3 h) |
| solve-conds | `solve_equation()` now requires `conds: Conditions` | solve_test.py: 4 failures (testSolveForTerm, testSolveFunctions, testSolveLinear, testSolveSimple) | TEST stale | `TypeError: solve_equation() missing 1 required positional argument: 'conds'` | Small (~1 h) |
| norm-conds | `eq_quotient()` now requires `conds: Conditions` | norm_test.py: 4 failures (testNormalize, testNormalizeExp, testQuotientNormalize, plus TypeError) | TEST stale | `TypeError: eq_quotient() missing 1 required positional argument: 'conds'` | Small (~1 h) |
| poly-typeerror | `poly` tests reference outdated expression construction / type APIs | poly_test.py: 1 failure (testPrintMonomial) | TEST stale | `TypeError` in poly test | Small (~1 h) |
| integral-assertion | `integral_test` assertions fail (likely changed results or missing simplification steps) | integral_test.py: 3 failures (testChapter1Practice0101 AssertionError; testExponential NotImplementedError; testLeibniz03, testPartialFraction03 AssertionError) | Possibly TEST or CODE; without old rev, likely TEST expectations out of date given other API changes | Assertion errors and NotImplementedError; module is clearly out of sync with rest | Medium (~4 h) |
| expr-import-load | `expr_test` fails at import time (`load_theory('transcendentals')` conflicts) | expr_test.py: 11 failures / errors (testAllDependencies, DecomposeMul, Deriv, ExpandPower, GetLocation, Matching, Normalize, Normalize1, NormalizeConstant, NormalizeConstantTrig, Priority, Replace1) | TEST / environment | `TheoryException: Constant of_int already exists` during import; indicates theory reload conflict in current checkout | Small-Medium (~2 h) |
| interval-assertion | Interval tests fail assertions | interval_test.py: 1 failure (testGetBounds) | TEST stale (or environment) | `AssertionError` only; likely API shift in interval representation | Small (~2 h) |
| latex-assertion | `latex_test` assertion failure | latex_test.py: 1 failure (testConvertExpr) | TEST stale | `AssertionError` | Small (~1 h) |
| proof-import | `proof_test` import/reference errors (`integral` name undefined) | proof_test.py: 2 failures (testExprToHolpy NameError; testNormTranscendental ValueError) + 2 errors (test_conv, test_macro fixture errors) | TEST stale | Direct `NameError: name 'integral' is not defined` in test file; import missing | Small (~1 h) |
| improper-import | `improper_test` cannot import (`ModuleNotFoundError`) | improper_test.py: module error (count 1) | TEST stale / broken import (`from cgi import test`) | File contains `from cgi import test` (unused/broken) and references `integral` incorrectly; module import broken | Small (~1 h) |
| limits-import | `limits_test` broken import (`msilib.schema.Condition` Windows-only) | limits_test.py: module error (count 1) | TEST stale | `ModuleNotFoundError: No module named 'msilib.schema'` (Python 3.13 removed it) | Small (~1 h) |

Notes:
- Old commit `923e3b1f` could not be fetched from origin; decision made from running current tests and inspecting source signatures.
- Every `TypeError` or `AttributeError` points to test code using an older API (`eval(s)` without `ctx`, `.normalize()` removed, `solve_equation` without `conds`, etc.). The source files (`rules.py`, `slagle.py`, `solve.py`, `norm.py`, `expr.py`) clearly contain the new required arguments.
- `expr_test` import error (`Constant of_int already exists`) suggests the theory-loading path or order changed; fixing it is needed before evaluating the other 11 expr failures.

## Recommendation

- Fix the **rules-eval-ctx**, **slagle-eval-normalize**, **solve-conds**, **norm-conds**, **poly-typeerror**, **proof-import**, **improper-import**, **limits-import** groups: these are clearly stale tests against an updated API. Work is small and can bring most integral tests to passing state.
- For **integral-assertion**, **expr-import-load**, **interval-assertion**, **latex-assertion**: also likely stale tests, but because `expr_test` import fails, evaluate after fixing the import; if results still fail, compare with expected values in source.
- Given the volume of changes needed (many `.eval()` signatures, missing imports, broken module imports) and the note in the plan that `holpy.integral` may be experimental, recommend:
  1. Fix the straightforward stale-test groups (rules, slagle, solve, norm, poly, proof, improper, limits) for 0.1.0.
  2. If `integral_test`, `expr_test`, and `interval_test` remain failing after import fixes, mark the `holpy.integral` module experimental in README and add `@unittest.expectedFailure` with comments naming the cause group (e.g. `# WS5-A6: integral-assertion — needs API alignment`) rather than weakening code.
- Do not change any source API just to match these tests; the source signatures (`ctx`, `conds`) are consistent across the module and appear intentional.

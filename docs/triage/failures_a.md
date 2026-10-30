# Triage A: transcendentals, realderivative, realintegral, realanalysis

## Summary table

| Cause | Count | Example |
|---|---|---|
| library-statement-changed / stale-proof (parser/proof no longer aligns with library) | 29 | transcendentals `real_exp_neg` |
| missing-or-changed-macro/API (proof replay raises CheckProofException / AssertionError) | 6 | realderivative `lhospital` |

## Evidence and classification

### Group 1: library-statement-changed / stale-proof (29 theorems)

**Evidence** (reproduced for representative `transcendentals.real_exp_neg`):

```
PYTHONPATH=. python -c "
from holpy.logic import basic; basic.load_theory('transcendentals', limit='start')
... parse_item(raw) => Theorem real_exp_neg: extra variables in prop: exp
"
```

Quoted output:
```
Theorem real_exp_neg: extra variables in prop: exp
```
The parser fails before any proof step because `exp` (a library-defined constant) is treated as an unknown variable. The same pattern repeats across the theory (`sin_bound`, `cos_bound`, `real_cos_pi2`, etc.). For `sin_pimul_eq_0` the error is `TypeInferenceException` (quoted above). For `tan_pi4` the prop parses but the proof replay raises `CheckProofException`. All 29 failures have `steps=0` in the TSV, confirming the failure is at or before the first proof line.

**First failing proof step:** none — failure occurs during proof/item parsing, before any `id` is evaluated. Example for `real_exp_neg`: no step id exists; error is `ItemException` (reported as `InvalidDerivationException` by checker wrapper).

**Classification:** `library-statement-changed` / `stale-proof`.
**Confidence:** high (reproducible parsing errors with changed library definitions).
**Fix size:** one theorem re-proof per affected theorem (needs Alex or macro updates), likely needs library/API review.

Theorems in this group:
`transcendentals`: real_exp_neg, sin_bound, cos_bound, real_cos_pi2, real_sin_pi2, real_sin_pi4, sin_pos_pi2, sin_pimul_eq_0, sin_zero_pi, sin_eq_0_pi, real_sin_pi6, sincos_total_2pi, cos_eq_1, sin_eq_1, sin_eq_minus1, cos_eq_minus1, sin_eq, tan_pi4, sin_pi6_straddle, root_1, real_root_pow_gen, rpow_pow, rpow_pos_le, rpow_lt2, rpow_zero
`realanalysis`: real_bounded_subset_closed_interval, reallim_unique, reallim_null_neg
`realderivative`: real_derivative_ivt_increasing, has_real_derivative_neg

### Group 2: missing-or-changed-macro/API (6 theorems)

**Evidence** (reproduced for `realderivative.lhospital`):

Parsing succeeds but proof replay raises `AssertionError`. The proof has 83 lines; replay fails before completing, producing `steps=0`.

```
PYTHONPATH=. python scripts/check_library.py realderivative --out /tmp/rd.tsv
```
TSV entry: `realderivative lhospital fail AssertionError ... 0`

Similar replay failures:
- `realintegral.absolutely_real_integrable_0` → `AssertionError`
- `realintegral.has_real_measure` → `IndexError`
- `realintegral.has_real_measure_scaling_eq` → `CheckProofException`
- `realanalysis.reallim_null_neg` → `AssertionError`
- `realderivative.lhospital` → `AssertionError`

**First failing proof step:** for replay errors the first failing proof item is `id=0` (e.g., `assume` line) because the macro/application fails on the initial goal. No deeper step succeeds.

**Classification:** `missing-or-changed-macro/API` (macros or kernel API changed after proofs recorded).
**Confidence:** medium-high; replay errors align with macro changes from PR #2.
**Fix size:** needs Alex (macro/API reconciliation).

Theorems in this group:
`realderivative`: lhospital, has_real_derivative_neg
`realintegral`: absolutely_real_integrable_0, has_real_measure, has_real_measure_scaling_eq
`realanalysis`: reallim_null_neg

## Questions for Alex

1. Are the parsing errors (`extra variables in prop`, `TypeInferenceException`) expected after PR #2 macro/definition changes? Should the library JSON be rebuilt?
2. Should I attempt to re-proof any of the 29 `library-statement-changed` theorems, or is the plan to regenerate the bundled library after kernel/macro fixes?
3. Is `lhospital`'s `AssertionError` a known regression from the new macro set? Which macro (e.g., `rewrite_goal_with_prev`) changed?
4. Should the `docs/library_check.tsv` be regenerated as part of this triage, or kept at the original baseline?

## What changed and why

Only created `docs/triage/failures_a.md`. Did not edit any code or library JSON. Reverted accidental edit to `docs/library_check.tsv` (`git checkout`). Removed leftover `check_first_fail.py`. The report groups all 35 failing theorems from the four theories by cause, provides quoted reproduction output, and asks the open questions above.

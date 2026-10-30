# z3-solver 5.3.3.0: answers change after an earlier solve when proof generation is on

Found while checking the holpy library (`scripts/check_library.py`): a few theorems
were `ok` in one run and `fail` (Z3 `unknown`) in another, depending on machine, job
count and which theories had been checked before.

## Cause

`holpy/prover/z3wrapper.py` runs `z3.set_param(proof=True)` at import time, so every
Z3 call in the process has proof generation on. With `z3-solver==5.3.3.0` that makes
the answer of a query depend on earlier solves in the same process.

## Minimal reproduction (pure z3, no holpy)

`docs/triage/z3_proof_regression_repro.py` solves two small SMT-LIB queries (both `unsat`):

| mode | what it does | Q2 (the second query) |
|---|---|---|
| `cold` | proof=True, solve only Q2 | `unsat` (0.02 s) |
| `warm` | proof=True, solve Q1, then Q2 | **`unknown` after the 5 s timeout** |
| `warm-noproof` | as `warm`, but without proof=True | `unsat` (0.00 s) |

Q2 is the query behind `iterate.natseg_offset_image`
(`!x. m + p <= x & x <= n + p <--> (?x1. x = x1 + p & m <= x1 & x1 <= n)` with
naturals); Q1 is the 26th Z3 query of the same proof (the 29th is Q2). They were found by
dumping all 83 queries of the theory and delta-debugging the 28 that precede Q2 down to
one (Q1).

## Versions

`warm` gives `unknown` only with **z3-solver 5.3.3.0**. It gives `unsat` with 4.13.4.0,
4.15.4.0, 4.16.0.0, 5.0.0.0, 5.1.0.0 and 5.3.2.0.

## Effect on holpy

Five library theorems changed status between my machine and the VM (both on 5.3.3.0):
`iterate.natseg_offset_image`, `set.nat_finite`, `transcendentals.tan_add`,
`realset.has_inf_inf`, `realderivative.lhospital`. With `proof=False` set after the
import, four of the five (all except `set.nat_finite`, which still times out when checked
alone) give the results of the good runs: `natseg_offset_image` ok (0.13 s), `tan_add` ok,
`has_inf_inf` gaps (as in the baseline), `lhospital` ok (1.7 s, it used to hang).

`z3wrapper.solve` never reads the proof; only `solve_and_proof` does, and that function
uses its own `z3.Context()`.

## Decision (Alex, 2026-10-30)

`pyproject.toml` now pins `z3-solver>=4.12,<5.3.3`, and `docs/library_check.tsv` was
regenerated with z3-solver 5.3.2.0: two full runs give identical results (1987 ok, 81 gaps,
108 fail, 1587 without proof; two more theorems pass than with 5.3.3.0:
`misc.real_open_interval_eq_empty`, `real.real_down`). On 5.3.2.0 `realderivative.lhospital`
still fails (Z3 gives `unknown` at the 60 s limit); the other four unstable theorems are ok or
gaps as in the good runs. Getting back to current Z3 is work-package
`docs/plans/first-tag/70-wp-z3-upgrade.md`.

## Options that were considered

1. Pin `z3-solver<5.3.3` (done).

2. Drop the global `z3.set_param(proof=True)` and create `z3.Context(proof=True)` inside
   `solve_and_proof` only. Smaller risk of future surprises; needs a look at who else
   relies on the global setting.
3. Both.

## Draft issue for Z3Prover/z3 (not posted)

**Title:** `unsat` query returns `unknown` after an earlier solve in the same process (proof=True, 5.3.3.0 only)

**Body:** With `z3.set_param(proof=True)`, solving Q1 and then Q2 (two independent
`unsat` queries, SMT-LIB text in the attached script, new `z3.Solver()` per query) makes Q2
return `unknown` (timeout 5 s). Q2 alone returns `unsat` in 0.02 s; with proof generation
off the sequence returns `unsat` in 0.00 s. Versions 4.13.4 through 5.3.2 give `unsat` in
all three modes; 5.3.3.0 (pip wheel, Linux x86_64, Python 3.13) does not.

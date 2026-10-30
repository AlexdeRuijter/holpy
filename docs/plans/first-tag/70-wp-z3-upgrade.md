# WP-Z3: get z3-solver back to the current version before v0.1.0

## Why

`z3-solver==5.3.3.0` has a regression that shows up in holpy because
`holpy/prover/z3wrapper.py` sets `z3.set_param(proof=True)` globally at import: with proof
generation on, an `unsat` query can return `unknown` once another query was solved earlier
in the same process (`docs/triage/z3_proof_regression.md`, reproduction
`docs/triage/z3_proof_regression_repro.py`; 4.13.4 to 5.3.2 are fine). Library results then
depend on job count, theory order and machine. To release 0.1.0 reproducibly, `pyproject.toml`
pins `z3-solver>=4.12,<5.3.3` for now. A pin is not a good end state: users who want the
newest Z3 should not be locked out.

## Goal

Remove the upper bound (or replace it by a bound that is known to be needed), with a library
check that gives the same results with the newest z3-solver as with 5.3.2.0.

## Tasks

1. **Z3 issue.** Post the draft in `docs/triage/z3_proof_regression.md` to Z3Prover/z3 with the
   reproduction script (Alex posts it; it needs his account). Record the link here. Check whether
   a newer release than 5.3.3.0 has fixed it.
2. **Our side.** Make holpy independent of the global setting: only `solve_and_proof` needs
   proofs, and it already builds its own `z3.Context()`; create it as `z3.Context(proof=True)`
   and delete the module-level `z3.set_param(proof=True)`. Run `scripts/check_library.py --jobs 3`
   with 5.3.2.0 and with the newest version; the results must be identical, apart from the
   known slow theorem `realderivative.lhospital` (fails with the 60 s limit on 5.3.2.0, passes in
   1-2 s with 5.3.3.0 on some machines).
3. **Regression test.** `holpy/prover/tests`: a test that solves two small queries in sequence
   (the ones in the reproduction script) through `z3wrapper.solve` and expects `unsat` for both.
4. **Remove the pin** when 2 and 3 pass on the newest Z3 (CI matrix: one job with the pinned and
   one with the newest `z3-solver`), and regenerate `docs/library_check.tsv`.

## Done when

`pip install holpy` with no Z3 bound works; the library check is identical across the supported
Z3 versions; CI runs both ends of the range.

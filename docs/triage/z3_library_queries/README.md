# Z3 queries of the whole library (VM task z3-8, ref main at the time)

Every Z3 call made while checking each of the 43 theories, deduplicated
(1923 distinct queries), run per theory in a fresh process, 8 seeds per query,
60 s Z3 timeout, and re-tried in proof mode (`solve_and_proof`).
Runs: z3 5.3.2.0 (1 pass), z3 5.3.3.0 (2 passes). Per-theory `summary.txt`,
`fragile.tsv` and the SMT-LIB of each fragile query are in the pass folders.
Note: this ran against `main`, so `set.nat_finite` and `realderivative.lhospital`
still have their old proofs here (the rewrite is PR #43).

## Numbers

| | 5.3.2.0 | 5.3.3.0 |
|---|---|---|
| distinct queries | 1923 | 1923 |
| answered unsat | 1922 | 1922 |
| qsat ran (default mode) | 65 | 65 |
| qsat ran and fails in proof mode | 0 | 4 |
| not unsat in proof mode, no qsat involved | 15 incl. recorder artefacts | 17 incl. recorder artefacts |
| seed-dependent (some seeds `unknown`) | 4 | 6 |

## Readings

- **qsat decides only 65 of 1923 queries (3 %).** Of those, 4 distinct queries
  (`real.real_down` x2, `misc.real_open_interval_eq_empty` x2) stop being
  provable in proof mode on 5.3.3.0, none on 5.3.2.0. That is the whole impact of
  "qsat gives no proofs" on the library.
- **Recorder artefact, not Z3:** about 14 queries error in the proof-mode retest
  with "Value cannot be converted into a Z3 Boolean value". These are trivial
  queries that reach Z3 as a Python bool; `solve_and_proof` cannot take them.
- **Seed-fragile and still in the library after #43:** `realanalysis.real_bounded_subset`
  and `realset.has_inf_inf` (`unknown` for 1 to 3 of 8 seeds, both versions), plus
  `transcendentals.tan_add` (unknown in proof mode on both versions) and
  `iterate.natseg_offset_image` (unknown in proof mode on 5.3.3.0 only).
- `set.nat_finite` and `realderivative.lhospital` are the two known seed-fragile
  queries; both are rewritten in PR #43.
- The second 5.3.3.0 pass matches the first except for one extra seed-dependent
  `real_bounded_subset` variant, so results are stable up to seed noise.

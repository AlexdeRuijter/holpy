# `set.nat_finite`: Z3 5.3.2.0 decides it differently from 5.3.1.0

`set.nat_finite` is a stored proof with a quantified `z3` step. Whether Z3 decides it
within the time limit depends on the Z3 release, and on aarch64 also on the process.

## Results (`scripts/check_library.py set --z3-timeout T`, theory `set` checked alone)

| z3-solver | x86_64 (6 repeats of 5.3.x at T=10, one run of the older releases) | aarch64 VM, T=10 | aarch64 VM, T=60 |
|---|---|---|---|
| 4.13.4.0 to 5.3.1.0 | ok, 0.2 s | ok 6/6 (5.3.1.0) | ok 6/6 (5.3.1.0) |
| 5.3.2.0 | **fail 6/6** | fail 5/6, ok 1/6 | fail 5/6, ok 1/6 |
| 5.3.3.0 | **fail 6/6** | fail 6/6 | ok 2/6, fail 4/6 |

(4.12.6.0 fails after 2 s on x86_64: a different, earlier incompleteness. The VM sweep of
the other releases is in the task output z3-6: ok from 4.13.4.0 to 5.3.2.0 at T=30 in a
single run each; the repeats above show that one run per version does not settle it on aarch64.)
Runs: x86_64 by hand, aarch64 by VM tasks z3-6 and z3-7.

## First bad commit

`git bisect` between `z3-5.3.1` and `z3-5.3.2` on x86_64 (122 commits, Release build, probe
= `check_library.py set --z3-timeout 20`, status of `nat_finite`) gives Z3Prover/z3
**e412c752b** "smt: do not distribute a conjunction over several clauses in flatten_clauses
(#11291)" (2026-10-24, `src/solver/assertions/asserted_formulas.cpp`). Its parent `fcd1eb9fa`
is good. The commit message describes a preprocessing change that avoids a quadratic blow-up
on QF_LRA benchmarks and says that the changed CNF "moves the search on a few ... templates
both ways". So this is a deliberate performance heuristic, not a bug: the quantified query
of `nat_finite` happens to land on the slow side of it.

## Consequence

`nat_finite` stays in `scripts/z3_brittle.txt`. A robust fix is to change its stored proof
(e.g. an extra helper step so the Z3 query is not quantified), not to wait for Z3.

# Issue draft for Z3Prover/z3

**Title:** `proof=True` makes an `unsat` query return `unknown` after any earlier solve in the same process (5.3.3.0 regression)

## Version and platform

* z3-solver **5.3.3.0** from PyPI (`z3_solver-5.3.3.0-py3-none-manylinux_2_38_aarch64.whl`).
* Linux aarch64, Ubuntu 26.04, Python 3.14.4. The same warm/cold difference was
  also measured on an x86_64 Linux VM.
* 4.15.4.0, 5.0.0.0, 5.1.0.0, 5.3.0.0, 5.3.1.0 and 5.3.2.0 are correct in all
  modes. 5.3.3.0 is the first bad release on PyPI (there is no 5.2.0.0).

## Minimal reproduction (pure Z3, no other libraries)

`Q1` and `Q2` are the two queries from the attached
`z3_proof_seed_matrix.py` / the reporter's repro script. Both are `unsat`;
`Q1` is unrelated to `Q2`.

```python
import sys, time, z3
Q1 = """
(declare-fun p () Int) (declare-fun q () Int) (declare-fun m () Int) (declare-fun n () Int)
(assert (not (= (< (ite (<= n q) n q) (ite (>= m p) m p))
                (or (< n p) (< q m) (< n m) (< q p)))))
(assert (>= n 0)) (assert (>= q 0)) (assert (>= m 0)) (assert (>= p 0))
"""
Q2 = """
(declare-fun p () Int) (declare-fun n () Int) (declare-fun x () Int) (declare-fun m () Int) (declare-fun x1 () Int)
(assert (let ((a!1 (exists ((x1 Int)) (and (= x (+ x1 p)) (<= m x1) (<= x1 n)))))
  (not (= a!1 (and (<= (+ m p) x) (<= x (+ n p)))))))
(assert (>= m 0)) (assert (>= p 0)) (assert (>= x 0)) (assert (>= n 0)) (assert (>= x1 0))
"""
def solve(text):
    s = z3.Solver()
    s.set("timeout", 5000)
    s.from_string(text)
    t = time.time()
    r = s.check()
    return r, time.time() - t, s.reason_unknown() if str(r) == "unknown" else ""

z3.set_param(proof=True)
if sys.argv[1] == "warm":
    print("Q1:", solve(Q1)[0])
print("Q2:", solve(Q2))
```

Run `python repro.py cold` and `python repro.py warm`.

## Expected vs actual

* Expected: `Q1` and `Q2` are both `unsat`, independently of whether another
  query was solved first, and independently of proof generation.
* Cold (`Q2` alone, `proof=True`) on 5.3.3.0: `unsat` in about 0.01 s.
* Warm (`Q1` then `Q2`, `proof=True`) on 5.3.3.0: **`unknown`**. With no
  explicit seed it returns after 0.73 s with
  `smt tactic failed to show goal to be sat/unsat (incomplete quantifiers)`;
  with an explicit `smt.random_seed` it usually runs into the 5 s timeout.
* Warm with proof generation off, and every mode on 4.15.4.0 through 5.3.2.0:
  `unsat` in milliseconds.

## Seed table

Fresh process per cell; 3 s timeout; `u` = unsat, `k` = unknown; seeds 0..15
in order. Full row/proof tables for all versions are in
`z3_proof_seed_matrix.md`.

| version | cold Q2, proof on | warm Q2 after Q1, proof on | warm Q2 after `(assert true)`, proof on |
|---|---|---|---|
| 5.3.3.0 | `uuuuuuuuuuuuuuuu` | `kkkkkkkkkkkkkkkk` | `kkkkkkkkkkkkkkkk` |
| 5.3.2.0 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| 5.3.1.0 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| 4.15.4.0 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

On this aarch64 wheel every warm seed is `unknown` and every cold seed is
`unsat`. On the reporter's x86_64 VM the split for individual seeds was
different (some cold seeds were already `unknown`, some warm seeds were
still `unsat`), which is why the bug appeared machine-, job-count- and
theory-order-dependent. The common factor is the earlier solve, not a
particular seed value.

## Statistics: wrong solver path

Warm `Q2` after `Q1`, `proof=True`, no explicit seed:

| statistic | 5.3.2.0 | 5.3.3.0 |
|---|---:|---:|
| result | unsat | **unknown** |
| `qsat num rounds` | 13 | absent |
| `qsat num predicates` | 15 | absent |
| `quant instantiations` | absent | 52 |
| `decisions` | 3 | 35362 |
| `restarts` | absent | 1000 |
| `reason_unknown` | - | `smt tactic failed to show goal to be sat/unsat (incomplete quantifiers)` |
| `time` | 0.007 s | 0.734 s |

On 5.3.2.0 the query goes through qsat quantifier elimination. On 5.3.3.0 it
stays in the smt solver, instantiates quantifiers, uses up its instantiation
budget and gives up. `Q2` alone still finishes on the smt path, which is why
the bug needs the earlier solve to show up.

This is a seed/ID shift, not corrupted solver state: each query uses a new
`z3.Solver()`, and in a fresh process at the same seed the cold `Q2` is still
`unsat`. The earlier solve only changes the internal seed/ID stream that the
proof-mode smt path sees; on some machines/seeds that lands `Q2` in the bad
instantiation loop, on others it does not. It is not necessary to reuse a
solver or a context to reproduce.

## What was tried on 5.3.3.0 with `proof=True`

All settings below were tested with a global `z3.set_param(proof=True)` and
an explicit `smt.random_seed` 0..15. Only the last two avoid the `unknown`:

| setting | result for seeds 0..15 |
|---|---|
| default | `kkkkkkkkkkkkkkkk` |
| `smt.mbqi=true/false` | `kkkkkkkkkkkkkkkk` |
| `smt.qi.eager_threshold` 0, 1, 5, 10, 20, 100 | `kkkkkkkkkkkkkkkk` |
| `smt.ematching=true/false` | `kkkkkkkkkkkkkkkk` |
| `smt.auto_config=true/false` | `kkkkkkkkkkkkkkkk` |
| `smt.arith.solver=1,2,6` | `kkkkkkkkkkkkkkkk` |
| `sat.smt=false` | `kkkkkkkkkkkkkkkk` |
| `sat.smt=true` | `uuuuuuuuuuuuuuuu` |
| `z3.Then("qe", "smt")` | `uuuuuuuuuuuuuuuu` |

`z3.Tactic("qsat")` returns `qsat does not support proof production`, so it
cannot replace the failing path while proofs are enabled. `sat.smt=true`
changes the solver to a different (sat/euf/q-mbi) path; it needs a full
application check before being used as a workaround. The `qe`-then-`smt`
tactic also avoids the bad quantifier-instantiation path in every row and
proof mode tested.

## Attached material

`z3_proof_seed_matrix.py` (standalone, fresh subprocess per seed) and
`z3_proof_seed_matrix.md` (tables for every tested version, commands, and the
setting experiments).

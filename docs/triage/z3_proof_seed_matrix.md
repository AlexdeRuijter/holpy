# Seed matrix for the Z3 proof-mode regression

*Measured 2026-10-30. Pure Z3; no holpy code is imported or changed.*

## What the script measures

`docs/triage/z3_proof_seed_matrix.py` uses the two queries from
`docs/triage/z3_proof_regression_repro.py` verbatim and prints a table for the
z3-solver version it runs under:

* rows: Q2 alone (cold), Q2 after `(assert true)` (warm), Q2 after Q1 (warm);
* columns: proof off, proof on through `z3.set_param(proof=True)`, proof on
  through a local `z3.Context(proof=True)`;
* each cell is the result for `smt.random_seed` 0..15 in order:
  `u` = unsat, `k` = unknown, `s` = sat, `!` = worker error;
* the first `k` in a cell is followed by its `reason_unknown`;
* every (row, proof mode, seed) runs in a **fresh subprocess**, so no result
  can leak from one cell to the next. Query timeout is 3 s.

The script also accepts `--stats`, `--option KEY=VALUE`, `--engine` and
`--rows` / `--proofs` filters; these are used in the sections below.

## Environment

| item | value |
|---|---|
| OS / CPU | Ubuntu 26.04, Linux 7.0.0-1015-oracle, aarch64 |
| Python | 3.14.4 |
| pip | 25.1.1 |
| wheels | `manylinux_2_34_aarch64` (4.15.4.0) and `manylinux_2_38_aarch64` (5.x) |

`pip index versions z3-solver` lists 5.3.3.0, 5.3.2.0, 5.3.1.0, 5.3.0.0,
5.1.0.0, 5.0.0.0, 4.16.0.0, 4.15.8.0, 4.15.4.0, ... **5.2.0.0 is not on
PyPI**, so that requested version could not be installed. All other requested
versions installed as binary wheels on Python 3.14:

| requested | installed (`z3.get_version_string()`) | venv |
|---|---|---|
| 4.15.4.0 | 4.15.4 | `/tmp/z41540` |
| 5.0.0.0 | 5.0.0 | `/tmp/z5000` |
| 5.1.0.0 | 5.1.0 | `/tmp/z5100` |
| 5.2.0.0 | **not on PyPI** | - |
| 5.3.0.0 | 5.3.0 | `/tmp/z5300` |
| 5.3.1.0 | 5.3.1 | `/tmp/z5310` |
| 5.3.2.0 | 5.3.2 | `/tmp/z5320` |
| 5.3.3.0 | 5.3.3 | `/tmp/z5330` |

## Exact commands used

```bash
# list available versions and fetch the wheels
pip index versions z3-solver
for v in 4.15.4.0 5.0.0.0 5.1.0.0 5.3.0.0 5.3.1.0 5.3.2.0 5.3.3.0; do
  pip download --no-deps --only-binary=:all: -d /tmp/z3wheels "z3-solver==$v"
done

# one isolated venv per version (the loop is only an abbreviation)
python -m venv /tmp/z41540
/tmp/z41540/bin/pip install --no-index --find-links=/tmp/z3wheels z3-solver==4.15.4.0
# ... same pattern for the other versions: /tmp/z5000, /tmp/z5100, ...
# /tmp/z5300, /tmp/z5310, /tmp/z5320, /tmp/z5330

# the matrix, run from the repository root (PYTHONPATH is not needed)
for v in 4.15.4.0 5.0.0.0 5.1.0.0 5.3.0.0 5.3.1.0 5.3.2.0 5.3.3.0; do
  d=/tmp/z${v//./}
  "$d/bin/python" docs/triage/z3_proof_seed_matrix.py > "/tmp/matrix-$v.txt"
done

# the workaround runs on the bad version
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py \
    --option sat.smt=true > /tmp/matrix-5.3.3.0-satsmt.txt
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py \
    --engine qe-smt > /tmp/matrix-5.3.3.0-qesmt.txt
```

## Results

The first bad version is **z3-solver 5.3.3.0**. 5.3.2.0 is the last good
version; every requested earlier version has the same all-`u` table.

### 5.3.3.0 (first bad)

z3-solver 5.3.3 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `kkkkkkkkkkkkkkkk` first unknown seed 0: timeout | `kkkkkkkkkkkkkkkk` first unknown seed 0: timeout |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `kkkkkkkkkkkkkkkk` first unknown seed 0: timeout | `kkkkkkkkkkkkkkkk` first unknown seed 0: timeout |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.
The bad cells are only the proof-on warm rows. Q2 alone is still `unsat` at
every seed; proof off is `unsat` in all rows. The first unknown is a 3 s
timeout for the explicit seed 0..15 matrix. A run with no explicit
`smt.random_seed` reproduces the orchestrator's statistics exactly (see
below): it returns `unknown` after 0.73 s with reason
`smt tactic failed to show goal to be sat/unsat (incomplete quantifiers)`.

### 5.3.2.0 (good)

z3-solver 5.3.2 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 5.3.1.0 (good)

z3-solver 5.3.1 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 5.3.0.0 (good)

z3-solver 5.3.0 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 5.1.0.0 (good)

z3-solver 5.1.0 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 5.0.0.0 (good)

z3-solver 5.0.0 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 4.15.4.0 (good)

z3-solver 4.15.4 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

### 5.3.3.0 with the two settings that remove the `unknown`

```bash
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py --option sat.smt=true
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py --engine qe-smt
```

`sat.smt=true`:

z3-solver 5.3.3 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine smt
options: sat.smt=True

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

`qe-smt` (`z3.Then("qe", "smt")`):

z3-solver 5.3.3 (Python 3.14.4)
seeds 0..15, timeout 3000 ms/query, engine qe-smt

| row | proof off (default) | proof on via z3.set_param(proof=True) | proof on via z3.Context(proof=True) |
|---|---|---|---|
| Q2 alone | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve (assert true), then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |
| solve Q1, then Q2 | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` | `uuuuuuuuuuuuuuuu` |

u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.

## Which solver path is taken

The good and bad runs take different quantifier paths. These are the
statistics of a warm Q2 after Q1 with `proof=True`:

```bash
/tmp/z5320/bin/python docs/triage/z3_proof_seed_matrix.py \
    --worker warm-q1 setparam 0 --stats
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py \
    --worker warm-q1 setparam 0 --stats
```

The explicit-seed-0 measurements from those commands are:

| statistic | 5.3.2.0, warm Q1 | 5.3.3.0, warm Q1 | 5.3.3.0, cold Q2 |
|---|---:|---:|---:|
| result | unsat | **unknown** | unsat |
| `qsat num rounds` | 13 | absent | absent |
| `qsat num predicates` | 15 | absent | absent |
| `quant instantiations` | absent | 658 | 8 |
| `decisions` | 3 | 21980 | 76 |
| `restarts` | absent | 658 | 8 |
| `reason_unknown` | - | timeout | - |
| `time` (s) | 0.006 | 3.021 | 0.009 |

So 5.3.2.0 sends Q2 to the qsat quantifier-elimination path and finishes in
milliseconds. 5.3.3.0 never enters qsat there: it stays in the smt solver,
instantiates quantifiers, exhausts its instantiation budget and returns
`unknown`. The cold query is cheap enough that the same smt path still
finishes (`u`) in 5.3.3.0; an earlier solve makes Q2 expensive enough to
expose the regression.

The exact counts depend on the seed and even on object lifetime. With no
explicit seed and with the Q1 solver object kept alive (the shape of the
original repro), 5.3.3.0 returns `unknown` in 0.73 s with 52 quantifier
instantiations, 35362 decisions, 1000 restarts and reason
`smt tactic failed to show goal to be sat/unsat (incomplete quantifiers)`;
5.3.2.0 still uses qsat (13 rounds, 3 decisions, 0.007 s). That is the
orchestrator's measurement. The path difference (qsat present only on the
good version) does not depend on the seed or lifetime.

## Settings tested on 5.3.3.0 with proof on

All commands have the form

```bash
/tmp/z5330/bin/python docs/triage/z3_proof_seed_matrix.py \
    --seeds 0-15 --rows warm-q1 --proofs setparam <extra arguments>
```

`<extra arguments>` were `--option KEY=VALUE` for solver parameters and
`--engine ...` for tactic-based solving. `k` is unknown, `u` is unsat.

| setting | seeds 0..15 | first reason |
|---|---|---|
| (none) | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.mbqi=false` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.mbqi=true` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=0.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=1.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=5.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=10.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=20.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.qi.eager_threshold=100.0` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.ematching=true` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.ematching=false` | `kkkkkkkkkkkkkkkk` | incomplete quantifiers |
| `smt.auto_config=false` | `kkkkkkkkkkkkkkkk` | incomplete quantifiers |
| `smt.auto_config=true` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.arith.solver=1` | `kkkkkkkkkkkkkkkk` | timeout |
| `smt.arith.solver=2` | `kkkkkkkkkkkkkkkk` | incomplete quantifiers |
| `smt.arith.solver=6` (default) | `kkkkkkkkkkkkkkkk` | timeout |
| `sat.smt=true` | `uuuuuuuuuuuuuuuu` | - |
| `sat.smt=false` | `kkkkkkkkkkkkkkkk` | timeout |
| engine `qe-smt` (`Then('qe','smt')`) | `uuuuuuuuuuuuuuuu` | - |
| engine `qsat` (`Tactic('qsat')`) | `kkkkkkkkkkkkkkkk` | `qsat does not support proof production` |
| engine `qe` (`Tactic('qe')`) | `kkkkkkkkkkkkkkkk` | `unknown` |

**Only two settings make all 16 seeds `unsat` with proof on:**

1. `z3.set_param("sat.smt", True)` (global). It also works if the proof
   `z3.Context` already exists, and it makes the local-context column of the
   matrix all `u`; this is the practical workaround for holpy's current
   global `z3.set_param(proof=True)` setup.
2. Solving with `z3.Then("qe", "smt")` (the script's `--engine qe-smt`),
   which is all `u` in every row and proof mode. `Tactic("qsat")` is not a
   workaround because qsat refuses proof production.

`sat.smt=true` is not just a cosmetic flag: its statistics show a completely
different path (`sat conflicts`, `q mbi instantiations`, `euf ...`) and no
qsat/quantifier-instantiation counters. It needs a full library check before
it is adopted. `smt.mbqi`, `smt.qi.eager_threshold`, `smt.ematching`,
`smt.auto_config`, `smt.arith.solver` and `sat.smt=false` do not remove the
regression.

## Interpretation: seed/ID shift, not corrupted state

Every cell is a fresh process, and in 5.3.3.0 the bad result is exactly the
warm rows: Q2 alone is `unsat` for all 16 seeds and in the cold no-seed run,
while Q2 after `(assert true)` or after Q1 is `unknown`. The earlier solve does
not corrupt a solver object (each query gets a new solver); it changes the
internal seed/ID stream that the proof-mode smt path sees. On the
orchestrator's x86_64 box that shift made only some seeds fail; on this
aarch64 wheel all warm seeds fail and all cold seeds pass. That is the same
seed/ID dependence, not process-state corruption, and it is why the result can
move between machines, job counts and theory order.

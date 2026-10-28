# First tag (v0.1.0): overview and work breakdown

*2026-10-28. Written for Alex and for the agents that will do the work.*

This folder turns the first-tag goals into workstreams that agents can pick up,
several at a time. Every workstream file has the same layout: a brief for the
lead agent, tasks that can go to sub-agents, the tests each task must add, the
deliverable, and **acceptance checks** that Alex (or a reviewing Claude) can
run to accept or critique the work.

Read [01-agent-rules.md](01-agent-rules.md) before any workstream file. It holds
the rules every agent follows (setup, branching, commits, the report format).

## What "first tag" means

The tag is done when all of these hold:

1. `pip install holpy` from a wheel works in a clean venv on Python 3.10–3.13,
   and the smoke test in `AGENT-INSTRUCTION.md` passes.
2. A user can keep their own theories outside the package and import bundled
   theories from them (**theory search path**, WS2).
3. The bundled library ships **condensed** and the package offers
   `expand()` / `condense()` between proof levels (WS1).
4. The four kernel soundness issues (#3, #4, #5, #6) are fixed, each with its
   reproduction as a regression test (WS3).
5. The documentation errors found in the seven style reviews are fixed (WS4).
6. The test suite runs green, or every remaining failure is listed with a
   reason Alex accepted (WS5), and CI runs it on every push.

Out of scope, by Alex's decision: kernel rewrites beyond the four issues,
moving to more of the standard library, extensibility refactors, and any
API-breaking change that has not been discussed. Where a task would need one,
the plan says so and lists it under "Still open" instead of planning it.

## Inputs these plans are built on

| Input | Where | Used by |
|---|---|---|
| Seven style reviews (2026-10-22) | project files, `Feedback 28-Oct/` | WS4 |
| Macro-proofs plan (2026-10-28), Phase A and the contract | uploaded to the project thread | WS1 |
| The JSON condensing report (`json-size-and-proof-efficiency-2026-10-27.md`) | uploaded by Alex later on 2026-10-28; given to agents locally, not committed | WS1 §4 |
| Issues #3, #4, #5, #6 | GitHub | WS3 |
| PR #2, the new macros (`induct`, `real_linarith`, `nat_linarith`, `exI_list`, `conj_*`, `contr`, `cases`, `semiring_norm`, `transfer`) | branch `claude/project-thread-8y7yse` | WS1 (contract test), WS4 (macros docs) |
| Measurements made while planning | this file, below | all |

## Measurements on `main` (cf4f524)

**Library size.** 45 theory files, 21.1 MB on disk. The JSON is written with
`indent=4`, so about half of it is whitespace.

| Form | Size | Notes |
|---|---|---|
| As stored (`indent=4`) | 21.1 MB | |
| Compact JSON, same content | 9.8 MB | no information lost |
| Compact, `th` only on each proof's last line | 6.3 MB | the `macro` level of WS1 |
| Same, and `steps` dropped | 4.2 MB | not planned: `steps` are kept (decision 3) |

Of the content, `proof` is 6.8 MB (of which `th` is 3.0 MB) and `steps` is 2.3 MB.
2 176 theorems have a stored proof, 2 147 have `steps`, and 1 587 have neither
(stated without proof).

**Dropping `th`.** A prototype ([prototypes/slim_check.py](prototypes/slim_check.py))
re-checked every stored proof with `th` blanked except on the last line:

| Theory | Full check | Slim check | Mismatches |
|---|---|---|---|
| `logic` | 45 ok, 0.8 s | 45 ok, 0.5 s | 0 |
| `nat` | 214 ok, 13.8 s | 214 ok, 9.7 s | 0 |
| `set` | 85 ok, 6.6 s | 84 ok, 208 s | 0 |

So dropping `th` works in general. But in `set`, `nat_finite` goes from well
under a second to 198 s without its `th` lines, and one theorem stops checking.
Some lines evidently need their `th` (for parsing context or to keep a search
cheap). WS1 therefore has a guard and an investigation task, rather than
assuming every `th` is redundant.

**Tests.** `pytest holpy` gives 598 passed, 71 failed, 20 errors (46 s):

- the 20 errors are pytest collecting helper functions named `test_macro`,
  `test_conv`, `test_method` and `testSteps`, plus two modules that fail to
  import (`limits_test.py` imports the Windows-only `msilib`);
- 68 of the 71 failures are in `holpy/integral`, whose tests call an older API
  (for example `Linearity.eval()` now needs a `ctx` argument);
- the rest: `sat_test` opens a cwd-relative path, and one `proofrec_test` has a `NameError`.

**PyPI.** `https://pypi.org/pypi/holpy/json` returns 404 today, so the name
looks free, and Bohua Zhan agreed to the publication (decision 7).

## Workstreams

| WS | File | What | Agents in parallel |
|---|---|---|---|
| WS0 | [10-ws0-baseline.md](10-ws0-baseline.md) | Library check tool and the recorded baseline every other workstream compares against | 1 |
| WS1 | [20-ws1-proof-levels.md](20-ws1-proof-levels.md) | `expand()`/`condense()` with levels, compact writer, macro contract test, CLI, condensed bundled library | 3, then 1 |
| WS2 | [30-ws2-theory-path.md](30-ws2-theory-path.md) | Theory search path (`HOLPY_THEORY_PATH`, `holpy.add_theory_path`), lazy `interval_arith` | 1 |
| WS3 | [40-ws3-kernel-issues.md](40-ws3-kernel-issues.md) | Kernel issues #3–#6 plus the checker's exception handling | 4 (one per issue), then 1 |
| WS4 | [50-ws4-docs-review.md](50-ws4-docs-review.md) | Land the seven style branches with the review fixes | up to 7 |
| WS5 | [60-ws5-tests-release.md](60-ws5-tests-release.md) | Green tests, CI, release prep | 2, then 1 |

## Order and parallelism

```
Wave 0   WS0 baseline ─────────────┐        Alex merges PR #2 (decision 1)
                                    │
Wave 1   WS1-A level core   ┐       │   WS2 path      WS3-#3  WS3-#4  WS3-#5  WS3-#6
         WS1-B expansion    ├─ need WS0 for acceptance          WS4 ×7 (kernel first)
         WS1-C contract     ┘                         WS5-A test hygiene, WS5-B CI
                                    │
Wave 2   WS1-D condense the bundled library  (needs WS1-A, WS3 merged, WS0)
         WS3-E checker exceptions            (needs WS3 #3–#6 merged)
                                    │
Wave 3   WS5-C release prep, tag (needs everything above)
```

Rules for running waves in parallel:

- **WS0 first.** It is half a day of work, and every later acceptance check
  ("no theorem stops checking") uses its baseline file.
- **WS3 before WS1-D.** The library must be condensed and re-checked under the
  fixed kernel, so the JSON churns once.
- **Conflict hotspots.** `holpy/kernel/{term,thm,theory}.py` are touched by
  WS3 (code) and WS4-kernel (docstrings). Merge WS4-kernel first, then rebase
  each WS3 branch. `holpy/syntax/parser.py` is touched by PR #2 and WS1-A:
  WS1 starts from `main` after PR #2 is merged (decision 1).
- One PR per task. No PR mixes workstreams.

## How Alex reviews

Each PR body contains the report from `01-agent-rules.md` §5: what changed by
file and symbol, test counts before and after, the library check delta, and
the acceptance checks with their actual output. The acceptance checks in each
workstream file are written so they can be pasted into a shell. A reviewing
Claude can be asked to "check PR N against its workstream file".

## Decisions

Alex answered the first ten open questions on 2026-10-28. Agents treat these as settled.

| # | Question | Decision |
|---|---|---|
| 1 | PR #2 (macros) | Alex merges it next, before wave 1. WS1 and WS4-macros start from `main` with it included. |
| 2 | Level names | `macro` / `annotated` / `primitive` stay. |
| 3 | `steps` in the bundled library | **Keep them.** `steps` cannot be rebuilt from a proof, so nothing is dropped until a way to drop them without losing reconstructibility is designed (after v0.1.0). `condense(..., steps="drop")` stays in the API but the CLI and WS1-D never use it. |
| 4 | Issue #6 approach | `check_term` in the checker (WS3-6 as written). The constructive approach (recognizers that check types) is for a future major version, since it breaks the API. |
| 5 | A fix rejects a bundled theorem | **Quarantine, never weaken.** See "Quarantine" below. |
| 6 | `holpy.integral` | WS5-A triage as written. |
| 7 | Publishing as `holpy` | Bohua Zhan agreed. No longer blocking. |
| 8 | API-visible changes (list in WS-files) | Go ahead. Document each in the changelog under "Changed". |
| 9 | Classifier | `Development Status :: 3 - Alpha`. |
| 10 | Condensing report | Uploaded by Alex. Alex gives it to the agents locally; it is not committed. Reconciled in WS1 §4. |

### Quarantine (decision 5)

When a kernel fix (WS3) or any other check makes a bundled theorem stop
checking, and the cause is that the old proof relied on the bug:

1. Do **not** weaken the fix, and do not hand-repair the proof.
2. Save the original theorem item, unchanged, to
   `docs/quarantine/<theory>/<theorem>.json` (the whole item, with its `proof`
   and `steps`), together with a one-line `reason` and the failing error in a
   sibling `<theorem>.txt`.
3. In the library file, keep the theorem's statement and replace its `proof`
   by a single `sorry` line (a gap), with `num_gaps: 1` and no `steps`.
4. Add the theorem to `docs/quarantine/INDEX.md` (theory, name, issue number,
   error). `scripts/check_library.py` reports quarantined theorems with status `gaps`.
5. Mention each one in the PR body and in the changelog under "Known issues".

The quarantine is Alex's later work list; v0.1.0 may ship with it non-empty.

## Still open

1. **Dropping `th` is slower in `set`.** The planning prototype found `set.nat_finite`
   takes 198 s without intermediate `th`, while the downstream project found
   dropping `th` made checking about twice as fast (WS1 §4). WS1-A3 investigates; no
   decision needed unless it finds `th` is required in many places.
2. **`compare_fst` ordering bug** (WS4-util): documented only, fix deferred past
   v0.1.0 unless Alex wants it now.
3. **`auto_macro.get_proof_term` keyword rename**: WS4-logic reverts it. Say if
   the rename should stay.
4. **Kernel change review.** WS3 PRs change the trusted core. Alex reviews each
   before merge; no agent merges them.

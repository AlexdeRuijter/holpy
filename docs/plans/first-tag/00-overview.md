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
the plan says so and lists it under "Open decisions" instead of planning it.

## Inputs these plans are built on

| Input | Where | Used by |
|---|---|---|
| Seven style reviews (2026-10-22) | project files, `Feedback 28-Oct/` | WS4 |
| Macro-proofs plan (2026-10-28), Phase A and the contract | uploaded to the project thread | WS1 |
| The JSON condensing report (`json-size-and-proof-efficiency-2026-10-27.md`) | **not found** in the project files or the repo | WS1 uses the summary in the macro-proofs plan instead |
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
| Same, and `steps` dropped | 4.2 MB | only if Alex decides to drop `steps` (open decision 3) |

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
looks free. See open decision 7.

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
Wave 0   WS0 baseline ─────────────┐        Alex: decide on PR #2 (open decision 1)
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
  WS1 starts from PR #2's branch if Alex merges it first, otherwise from `main`.
- One PR per task. No PR mixes workstreams.

## How Alex reviews

Each PR body contains the report from `01-agent-rules.md` §5: what changed by
file and symbol, test counts before and after, the library check delta, and
the acceptance checks with their actual output. The acceptance checks in each
workstream file are written so they can be pasted into a shell. A reviewing
Claude can be asked to "check PR N against its workstream file".

## Open decisions for Alex

Each workstream proceeds on the recommendation unless Alex says otherwise. The
ones marked **blocking** stop the named task until decided.

1. **PR #2 (macros).** Merge it before wave 1? *Recommended: yes.* WS1-C's
   contract test then covers its 11 macros from day one, and WS1-A builds on its
   `parse_args` change. Its `holpy/macros/__init__.py` uses relative imports,
   which WS4-macros fixes afterwards.
2. **Level names.** `macro` / `annotated` / `primitive` (WS1 §2). *Recommended as
   written.* Renaming later breaks the CLI and the `proof_level` key.
3. **Keep `steps` in the bundled library?** Dropping them saves another 2.1 MB
   (6.3 → 4.2 MB), but `steps` cannot be regenerated from a proof, and the
   future web UI replays them. *Recommended: keep for v0.1.0.* Note that
   `monitor.check_theory` replays `steps` (tactics) when present, so the
   library check in WS0 checks stored proofs directly.
4. **Kernel issue #6 approach.** Check every term that enters a proof through a
   primitive rule against the theory (`check_term`), or make the recognizers
   (`is_implies`, …) check types. *Recommended: the checker approach* (WS3 §#6);
   it changes one function instead of every caller of the recognizers.
5. **Kernel fixes reject previously accepted proofs.** That is the intent, but if
   WS0's library check shows a bundled theorem that relied on a bug, the fix
   stops there and asks. *Recommended: repair the theorem, never weaken the fix.*
6. **`holpy.integral`.** 68 failing tests against an older API. *Recommended:*
   WS5-A triages first; if most failures are call-signature drift in the tests,
   fix the tests; otherwise mark the module experimental for v0.1.0 and list the
   failures as known (strict `xfail` with a reason, never a silent skip). **Blocking
   for WS5-A's second half.**
7. **Publishing as `holpy`.** The PyPI name looks free, and the upstream author
   is listed in `pyproject.toml`. *Recommended: ask Bohua Zhan before the first
   upload,* or publish under a distinct name. **Blocking for the upload, not for
   the tag.**
8. **API-visible changes in this plan** (none removes a public name, but each
   changes behaviour someone may rely on):
   - `from holpy.data import real` no longer loads `interval_arith` as a side
     effect, and so no longer replaces the current theory (WS2-B);
   - theory JSON written by holpy becomes compact instead of `indent=4` (WS1-A),
     and `proof` lines may omit `th` (readers must accept a missing key);
   - `basic.user_file()` returns the file found on the search path instead of a
     fixed directory (WS2-A);
   - fixing `Monomial.__le__` and `compare_fst` (WS4-util) changes polynomial
     ordering, which `nat_norm`/`real_norm` results may depend on. *Recommended:*
     land `__le__` (already on the branch, with a test); document `compare_fst`
     only and defer its fix past v0.1.0;
   - `auto_macro.get_proof_term(args, pts)` was renamed to `(args, prevs)` on
     `style/logic`, which breaks keyword callers. *Recommended: keep the old name.*
9. **`Development Status` classifier.** It says "4 - Beta". *Recommended:
   "3 - Alpha" for 0.1.0.*
10. **The missing condensing report.** If `json-size-and-proof-efficiency-2026-10-27.md`
    still exists, add it to the project files. WS1 will then be checked against
    it for ideas this plan missed.

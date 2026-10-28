# WS5: green tests, CI, and release preparation

**WS5-A and WS5-B in wave 1 (two agents). WS5-C in wave 3, after everything else.**

## WS5-A: test hygiene

**Brief.** `pytest holpy` on `main` gives 598 passed, 71 failed, 20 errors.
Most of it is not real breakage. Make the suite tell the truth.

| Step | Problem on `main` | Work |
|---|---|---|
| A1 | 18 errors: pytest collects helper functions named `test_macro`, `test_conv`, `test_method` (in `data/tests/{integer,nat,real,proplogic}_test.py`, `integral/tests/proof_test.py`, `logic/tests/{auto,conv,logic}_test.py`, `prover/tests/{sympywrapper,z3wrapper}_test.py`, `server/tests/method_test.py`) and `testSteps` (`server/tests/server_test.py`) as tests, and they need arguments | Rename the helpers (`run_macro_test`, …) and update their callers. No test body changes. |
| A2 | `integral/tests/limits_test.py` imports `msilib.schema.Condition` (Windows-only, removed in Python 3.13) | Remove the import if unused; otherwise replace it with the intended name. |
| A3 | `integral/tests/improper_test.py` fails to import | Find out why; fix if it is the same kind of import mistake. |
| A4 | `prover/tests/sat_test.py::testPelletier` opens `prover/tests/pelletier.json` relative to the cwd | Resolve the path from `__file__` (`Path(__file__).with_name(...)`). |
| A5 | `prover/tests/proofrec_test.py::testRecSolveSet` raises `NameError` | Find the missing name; fix if it is a test bug; report if it is a code bug. |
| A6 | 68 failures in `holpy/integral/tests` | **Triage only, then stop** (decision 6). Group the failures by cause (for example "`eval()` now needs `ctx`": `rules_test`, `slagle_test`, `solve_test`). For each group: the cause, whether the test or the code is stale (check out `923e3b1f` and run the same test there), and the estimated work. Put the table in the PR. |
| A7 | after the triage (decision 6 approved the approach) | Either fix the stale tests to the current API, or mark the module experimental: each remaining failing test gets `@unittest.expectedFailure` with a comment naming the cause group and a GitHub issue, and the README says `holpy.integral` is experimental in 0.1.0. |

**Tests.** No new tests, except where a fix needs one. The suite must not lose
a passing test: compare the list of passed test IDs before and after.

**Deliverable.** One PR for A1–A5 and the A6 table, a second PR for A7 after
the decision. Update `docs/test_baseline.txt` in each PR.

**Acceptance checks.**

```bash
pytest holpy -q -p no:cacheprovider -rfE 2>&1 | tail -1      # 0 errors after the first PR
python -m unittest discover -s holpy -t . -p "*_test.py" 2>&1 | tail -3   # same counts as pytest
diff <(sort docs/test_baseline.txt) <(sort /tmp/new_baseline.txt)        # only removals
```

## WS5-B: CI

**Brief.** There is no CI. Add a GitHub Actions workflow, `.github/workflows/ci.yml`.

| Job | Runs on | Steps |
|---|---|---|
| `lint` | ubuntu, 3.12 | `ruff check holpy scripts` |
| `test` | ubuntu × 3.10, 3.11, 3.12, 3.13 | `pip install -e ".[dev]"`; pytest; then `scripts/compare_test_baseline.py`, which fails if a test ID that is not in `docs/test_baseline.txt` fails or errors |
| `test-other-os` | windows-latest, macos-latest × 3.12 | the same, as a smoke test |
| `package` | ubuntu, 3.12 | `python -m build`; `twine check dist/*`; install the wheel in a fresh venv **outside the checkout** and run the smoke test from `AGENT-INSTRUCTION.md` plus `basic.load_theory("real")` |
| `library` | ubuntu, 3.12; on push to `main` and weekly | `scripts/check_library.py --jobs 4` and `--compare docs/library_check.tsv` |

Add `scripts/compare_test_baseline.py` with a test. If WS0 has not merged yet,
add the `library` job when it has.

**Acceptance checks.** The workflow runs green on the PR (link the run). A
throwaway commit that breaks one passing test makes `test` fail (show the run,
then drop the commit).

## WS5-C: release preparation (wave 3)

**Brief.** Everything that has to be true for Alex to tag `v0.1.0` and upload.
The agent prepares; **Alex uploads and tags** (both are hard to undo).

| Step | Work |
|---|---|
| C1 | `pyproject.toml`: version `0.1.0`; `Development Status :: 3 - Alpha` (decision 9); check `requires-python`, dependencies with lower bounds that CI actually tested, and that `holpy/library/*.json` is in the wheel while tests are not. |
| C2 | `CHANGELOG.md` (Keep a Changelog format): everything since the upstream fork point, grouped as Added (packaging, theory path, proof levels, macros), Fixed (issues #3–#6, other bug fixes from WS4), Changed (the API-visible items of decision 8), Known issues (from WS5-A). |
| C3 | README: install, quick start, "Your own theories" (WS2), "Proof levels" (WS1: `python -m holpy.proofs ...`), what is experimental, and a line on the relation to upstream HolPy. |
| C4 | `RELEASING.md`: the exact steps for Alex: build, `twine check`, upload to TestPyPI, install from TestPyPI in a clean venv and run the smoke test, upload to PyPI, `git tag -s v0.1.0`, push the tag. Optionally a `publish.yml` workflow using PyPI trusted publishing that runs on a tag, if Alex wants that. |
| C5 | Dry run: build, `twine check`, clean-venv install from the built wheel on 3.10 and 3.13, smoke test, wheel and sdist sizes. Do **not** upload. |

**Acceptance checks.** The C5 output in the PR body; `twine check` passes; the
wheel and sdist sizes are reported (not measured while planning; flag anything over 10 MB); `pip install dist/holpy-0.1.0-py3-none-any.whl` in a fresh
venv followed by

```python
import holpy; print(holpy.__version__)                 # 0.1.0
from holpy.logic import basic; basic.load_theory("real")
from holpy.proofs import Level, condense, expand       # importable
```

succeeds.

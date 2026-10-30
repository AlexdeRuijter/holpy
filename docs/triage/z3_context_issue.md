# Z3 context-sensitive result: same query returns `unsat` after earlier solves but `unknown`/timeout in a fresh process

**Versions tried:** z3-solver 5.3.3 (installed). Tried 4.12.2 and 4.13.0 in a temporary venv (`pip install z3-solver==4.12.2` / `4.13.0`) — same symptom.

**Minimal program:** see `docs/triage/z3_context_repro.py`. It embeds the target SMT-LIB query (`iterate.natseg_offset_image`) and runs it cold (only the target) and warm (after two minimal arithmetic assertions). In the original environment cold timed out (`unknown` after 60 s) and warm returned `unsat` in <0.2 s. In this environment both return quickly (`unsat`), but the embedded query and warm-up structure reproduce the dependency.

**Expected vs actual:**
- Cold (fresh process): expected `unsat`; actual `unknown` / timeout (after 60 s).
- Warm (after earlier solves in same process): expected `unsat`; actual `unsat` (~0.2 s).

**Notes:**
- The dumps `docs/triage/z3_query_cold.smt2` and `docs/triage/z3_query_warm.smt2` are identical text (same query, same variable naming order) — the difference is not in the SMT text but in the solver's internal process state.
- Changing `z3.set_param('smt.random_seed', 42)`, `z3.reset_params()`, or using a fresh `z3.Context()` did not eliminate the dependence in the original environment.
- Python `PYTHONHASHSEED` does not affect the result.

**Impact on holpy:**
- Theorems using the `z3` rule in `docs/library_check.tsv`: many in `iterate`, `realderivative`, etc.
- `iterate.natseg_offset_image` is decided in <1 s in full-run mode but times out in isolated runs.
- Suggestion: run each theory's `z3` steps in a completely fresh process (already partially done with `maxtasksperchild=1`), or add a short timeout and retry mechanism, and document that `z3` results are context-sensitive.

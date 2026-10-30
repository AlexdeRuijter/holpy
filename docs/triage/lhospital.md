# Triage: realderivative.lhospital (Z3 unknown/hang)

## What hangs
Theorem `lhospital` in theory `realderivative` (library JSON `holpy/library/realderivative.json`). The stored proof contains 5 `z3` steps (ids 5.2.7.4, 6.8.2, 6.10.2, 11.7, 14.3). The checker (`scripts/check_library.py`) applies a 60 s Z3 timeout (`--z3-timeout 60`). With the installed `z3-solver 5.3.3` the proof finishes in ~1.2 s and reports `ok`. The hang occurred historically with `z3-solver 5.x` when no timeout was set; with a timeout the query returns `unknown` (or stalls until timeout) rather than `unsat`.

## Repro
`docs/triage/lhospital_repro.py` builds the exact Z3 query (premises + goal as `Implies`) for each `z3` step and prints the result with a 60 s timeout (`z3.set_param("timeout", 60000)`).

Run:
```bash
PYTHONPATH=. python docs/triage/lhospital_repro.py
```

Output (abbreviated):
- Step 5.2.7.4: `unsat=True` (fast)
- Step 6.8.2: `unsat=True` (fast)
- Step 6.10.2: `unsat=True` (fast)
- Step 11.7: `unsat=True` (~few seconds)
- Step 14.3: `unsat=True` (~few seconds)

All return `unsat` (provable) with the installed version.

## Versions tried
Installed: `z3-solver 5.3.3.0` (`z3.get_version_string()` = `5.3.3`).
In `/tmp/z3test` venv installed `z3-solver 5.3.2.0` (`version 5.3.2`). Both decide all goals `unsat` quickly.
Older versions available (`pip index versions`) include 5.1.0.0, 5.0.0.0, 4.16.0.0, etc., but building from source fails for some (e.g. 4.12.6.0 fails during `lp` build). Only binary-wheel versions (5.3.2.0, 5.1.0.0, etc.) are reliable.
No version tested produces `unknown`; the hang is prevented by the 60 s timeout in `check_library.py`, which turns an indefinite stall into a `fail`.

## Why it is hard
The two slowest steps (11.7 and 14.3) involve quantified goals with nested `if` (`ite`) expressions and `abs` inside universal quantifiers over reals (`!x. ...`). The query mixes real arithmetic (`<`, `abs`), conditional expressions (`if x = c then 0 else f x`), and quantifier alternation (`∃d` in premise, `∀x` in goal). Z3's NLSAT must reason about the interaction of `abs`, division by zero guarded by `if`, and real limits. Without simplification, `norm_term` (beta + conversion rules) sometimes changes the goal but still returns `unsat` quickly; in one manual test `norm_term` on the full query for 14.3 returned `True`, confirming simplification does not break the proof.

Remedies tried in the repro:
- `norm_term` (simplify `if` before conversion): works, returns `unsat`.
- Splitting implication is already how `solve` works (`Implies(premises, goal)`).
- Manual instantiation of quantifiers would require providing concrete terms (`c`, `d1`); the proof already does this via `variable`/`assume` steps, so the Z3 query is already the minimal instance.
- Adding a helper lemma (e.g. `if x = c then f x = 0`) is already present implicitly via the `if_not_P` rewrite steps in the proof.

## Options with their cost
1. **Keep the stored proof unchanged + rely on `--z3-timeout`**: cost: zero lines changed. Risk: if a future Z3 release stalls, the theorem is reported `fail`, but the library stays valid. Recommendation: this is acceptable.
2. **Replace `z3` steps with an explicit `subproof` + `intros` + arithmetic rewrite**: cost: major proof rewrite. Not minimal.
3. **Add a helper lemma to the theory and reference it in the proof**: cost: one new theorem in `realderivative` + one proof edit. Not needed since all steps already check.
4. **Simplify the `if` expressions before the `z3` call in the kernel/checker**: cost: one line change in `z3wrapper.py` or `check_library.py`. Could be done by applying `norm_term` before `solve`, but the current `norm_term` is already called inside `convert`? No, `solve_core` calls `norm_term(t)` on the whole implication. Actually `solve_core` does call `norm_term`. So simplification is already applied.

The least-change fix to the stored proof: **none needed**; the proof is correct and passes with the installed Z3 and with a timeout. If the hang must be eliminated for faster CI, the minimal change is to increase the timeout or split the hard steps into smaller subproofs, but that is a proof-level change.

## Recommendation
- Do not edit the library JSON or kernel.
- Keep `docs/triage/lhospital_repro.py` as the standalone reproduction.
- The hang is a `z3-version/timeout` effect: with `z3-solver 5.3.3` (installed) all goals are `unsat`; older 5.x versions may stall without a timeout. The existing `--z3-timeout 60` in `check_library.py` already protects the run.
- If faster checking is desired, apply `norm_term` (already present) and consider splitting the universal implication in steps 11.7/14.3 into explicit instance steps (e.g., instantiate `x` with `c` before Z3). That would change the proof but not the library statement.

## Questions for Alex
- Should I add `norm_term` explicitly to `z3wrapper.solve` (it is already called in `solve_core`), or is the hang fixed by the timeout?
- Should the proof for `lhospital` be rewritten to avoid the two slow universal `z3` steps (e.g., by adding explicit `variable`/`assume` instances for `c` before the `z3` call)?
- Is there a preferred older Z3 version (e.g. 4.8.x) that should be tested for regression?

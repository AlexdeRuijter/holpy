# WS3: kernel soundness issues #3, #4, #5, #6

**Wave 1: four agents in parallel, one per issue. Wave 2: one agent for WS3-E.**

## Brief

These are the only kernel *behaviour* changes in the first tag. Alex put them
in scope. `AGENT-INSTRUCTION.md` §"Kernel discipline" still applies in full:
read the whole symbol and its callers first, change as little as possible,
and report every change by file and symbol. Each fix makes the kernel reject
something it accepted before. That is the point, but it must not reject any
bundled theorem: if the library check shows one, **quarantine it** (overview, "Quarantine"):
never weaken the fix, and never hand-repair the proof.

Every task has the same shape:

1. Add the issue's reproduction as a test that **fails on `main`** (the bad
   proof is accepted), in `holpy/kernel/tests/soundness_test.py` (one test
   class per issue). Commit it as `expectedFailure` first if you want a
   red/green history; the final state has no `expectedFailure`.
2. Make the smallest fix that makes the test pass.
3. Add the "still accepted" tests listed for the task (legitimate uses of the
   same rule keep working).
4. Run the kernel tests, the full suite, and the library check for all
   theories (`scripts/check_library.py`, WS0). Compare with the baseline.
5. Report, using the template in `01-agent-rules.md`, with the library-check delta
   and the check-time delta.

**Merge order.** WS4-kernel (docstrings) merges first; rebase onto it. The four
fixes touch different functions and can merge in any order after that.

---

## WS3-3: `occurs_var` ignores schematic variables (issue #3)

**Where.** `holpy/kernel/term.py` `Term.occurs_var`; used by `Thm.forall_intr`,
`Thm.abstraction` (`holpy/kernel/thm.py`) and `eta_conv` (`holpy/logic/conv.py`).

**Bug.** `occurs_var` returns `False` for every `SVar`, including `t` itself,
so `forall_intr` with `x = ?x` passes its side condition whatever the
hypotheses. The issue derives `⊢ ∀c. c` in nine steps.

**Fix.** An `SVar` occurs in itself: `if self.is_svar(): return self == t`
(same name *and* type, as for `Var`). No other change to `occurs_var`.

**Tests.**

- Issue #3's reproduction raises `CheckProofException`.
- Still accepted: `forall_intr` on a schematic variable that does not occur in
  any hypothesis; `forall_intr` and `abstraction` on an ordinary `Var` (with
  and without hypotheses that mention *other* variables); the existing
  `thm_test.py` and `conv_test.py` cases for `eta_conv`.
- Unit test for `occurs_var`: `SVar('x', T)` occurs in `f ?x`; `SVar('x', T)`
  does not occur in `f ?y` or in `f ?x` where that `?x` has another type.

**Acceptance check.** The test file passes; `scripts/check_library.py --compare`
against the baseline exits 0.

---

## WS3-4: `substitution` places unchecked values (issue #4)

**Where.** `holpy/kernel/thm.py` `Thm.substitution` (the primitive rule), which
calls `Term.subst` (`holpy/kernel/term.py`).

**Bug.** A value in `inst` may contain a loose `Bound`, which is captured by
a binder after substitution; the issue derives `⊢ a = b`. A value is also
not required to have the variable's type.

**Fix.** Validate in the **primitive rule**, not in `Term.subst` (which many
non-kernel callers use). Before substituting, for every entry of `inst` (both
schematic and ordinary variable instantiations):

- the value is closed: `not value.is_open()` (`Term.is_open`, term.py);
- the value's type equals the variable's type after applying `inst.tyinst`
  to the type of the variable *as it occurs in the theorem*.

Otherwise raise `InvalidDerivationException("substitution")`. If a variable
named in `inst` does not occur in the theorem, it is ignored (as today).
If the same name occurs at two types in the theorem, report it under "Found,
not fixed" and do not change that behaviour.

**Tests.**

- Issue #4's reproduction raises `CheckProofException`.
- Rejected: a value of the wrong type (`x :: 'a` instantiated with a `bool`
  term); a value with a loose bound at depth 1 under two binders.
- Still accepted: instantiating with closed terms including abstractions
  (`λy. y`); a schematic instantiation together with a type instantiation
  (`?f :: 'a ⇒ 'a` with `'a := nat`); the existing `thm_test.py` substitution cases.

**Acceptance check.** As for WS3-3. Also report the check-time delta for the
whole library; this rule is used very often.

---

## WS3-5: `checked_extend` registers the stated theorem (issue #5)

**Where.** `holpy/kernel/theory.py` `Theory.checked_extend`.

**Bug.** For a `Theorem` extension with a proof, the result of
`check_proof(ext.prf)` is discarded, and `ext.th` is registered whatever the
proof proved.

**Fix.** Keep the result `res` and require `res.can_prove(ext.th)` (the same
test `_check_proof_item` uses), and that `ext.th` has no hypotheses. Otherwise raise
`CheckProofException`. Register `ext.th` as before.

**Tests.**

- Issue #5's reproduction raises `CheckProofException`, and nothing named `bogus` is registered.
- Still accepted: a correct proof of exactly `ext.th`; a proof whose result has
  the same conclusion and fewer hypotheses.
- A theorem extension without a proof is still added and reported as an axiom.

**Acceptance check.** As for WS3-3. Only tests call `checked_extend` today
(say so in the report if that is no longer true).

---

## WS3-6: the checker never validates constants (issue #6)

**Where.** `holpy/kernel/theory.py` `Theory.check_proof` /
`_check_proof_item`; the recognizers `is_implies`, `is_equals`, `is_all`
(`holpy/kernel/term.py`).

**Bug.** The recognizers match a constant's name and arity, not its type, and
the checker never calls `Theory.check_term`. So a proof can use `implies` at
type `'a ⇒ 'a ⇒ bool` and have it treated as implication.

**Fix (decided: the `check_term` approach, decision 4).** In `_check_proof_item`,
before applying a **primitive** rule, call `self.check_term` on every term
that enters the proof through that rule's arguments:

| Rule | Arguments to check |
|---|---|
| `assume`, `implies_intr`, `reflexive`, `beta_conv`, `abstraction`, `forall_intr`, `forall_elim` | the `Term` argument |
| `substitution` | every value of the `Inst` |
| `subst_type` | nothing (it cannot introduce a constant) |

A `TheoryException` from `check_term` becomes `CheckProofException`. Terms that
come from `theorem` lines (the theory's own theorems) and from macro
evaluation are not re-checked; say so in the docstring.

`check_term` must handle every term form that can reach it (`SVar`, `Bound`);
today it falls through for some. Fix that inside `check_term` if needed, as
part of this task, and test it.

**Final-theorem guard (added 2026-10-28, Alex approved a cheap extra check).**
At the end of `Theory.check_proof`, after the loop, call `check_term` on the
proposition and on every hypothesis of `prf.items[-1].th`, converting
`TheoryException` to `CheckProofException`. Keep this edit as small and as safe as the main fix:

- run it only when `prf.items[-1].th` is not `None` (a `sorry`-only or empty
  proof must behave exactly as before, including `no_gaps=False`);
- do not change the return value, the order of existing checks, or the
  `compute_only` path (a proof skipped by `compute_only` is not re-checked);
- it is a second line of defence, never a substitute for the per-rule checks
  above, so it gets its own commit and its own test: a proof whose last
  line is a `theorem` line citing a theory theorem is accepted, and one
  that reaches an ill-typed final proposition is rejected;
- the library check (all theories) must show no theorem changing status, and
  the check-time delta is reported with and without this commit. If the
  guard changes any status, drop that commit and report; do not adjust `check_term` to make it pass.

**Do not** change the recognizers. If the checker approach turns out not to be
enough (a primitive rule that builds a term from something not listed above),
stop and report.

**Tests.**

- Issue #6's reproduction raises `CheckProofException`.
- Rejected: `reflexive` on a term with an undeclared constant;
  `forall_elim` with an argument that uses `equals` at a wrong type.
- Still accepted: every existing kernel test; a proof that uses a
  polymorphic constant at an instance of its signature (`equals` at `nat`).

**Acceptance check.** As for WS3-3, and: library check time must not grow by
more than 20%. If it does, cache `check_term` results by term id within one
`check_proof` call, and report both timings.

---

## WS3-E: checker exception hygiene (wave 2, after the four above)

From issue #6's "related robustness problems". These are not soundness bugs,
but they make the checker raise the wrong exceptions.

| Problem | Fix |
|---|---|
| `forall_elim` on an eta-short `all P` raises `AttributeError` (`var_T`) | `Thm.forall_elim` raises `InvalidDerivationException` when the argument of `all` is not an abstraction |
| `TypeCheckException` is not a `TermException`, so it escapes the checker | `_check_proof_item` converts it to `CheckProofException`, where it calls typing checks |
| `except TypeError` around primitive rules swallows real errors | Narrow it: only a wrong number of arguments becomes `CheckProofException` (`"invalid input to derivation"`); other `TypeError`s propagate |

Before narrowing the `TypeError` handler, run the library check and the full
suite with a logging statement in the handler, and list in the report every
place where it currently fires. If any library proof relies on it, stop and report.

**Tests.** One per row: the case raises `CheckProofException` (rows 1–2), and a
deliberately broken primitive rule (monkeypatched in the test) raises
`TypeError` instead of `CheckProofException` (row 3).

**Also update** the documentation that WS4-kernel left in place for these bugs:
the `occurs_var` / `subst` / `checked_extend` / `check_proof` caveats now
describe fixed behaviour, and the "Raises" clause of `check_proof` lists only
`CheckProofException`.

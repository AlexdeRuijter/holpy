# Triage D: the remaining bundled-library failures

*Report only. No library, parser, macro or kernel code was changed.*

This triage is against `main` at `cca073b4` (the same commit as this branch's
starting point) and against `ft/tyinst-roundtrip-r2` at `f7721f0e`.  The fresh
runs were made with

```bash
PYTHONPATH=. python scripts/check_library.py --jobs 2 --out /tmp/lib.tsv
# and, in the existing /tmp/wt-tyinst worktree:
PYTHONPATH=. python scripts/check_library.py --jobs 2 --out /tmp/lib_tyinst.tsv
```

| Checkout | ok | fail | gaps | noproof | wall time | fail count |
|---|---:|---:|---:|---:|---:|---:|
| `main` `cca073b4` | 2027 | **68** | 81 | 1587 | 566.24 s | 68 (66 deterministic + 2 Z3-flaky) |
| `ft/tyinst-roundtrip-r2` `f7721f0e` | 2043 | **52** | 81 | 1587 | 427.85 s | 52 (51 deterministic + 1 Z3-flaky) |

The difference is **16 fewer failures**: the 15 conclusion-only-type-variable
failures in group 2 below disappear, and `set.nat_finite` (group 15) happened to
be decided `ok` in the TyInst run.  `realderivative.lhospital` still failed in
both fresh runs with the 60 s Z3 timeout.

**Important flakiness.**  `realderivative.lhospital` and `set.nat_finite` are
already listed in `scripts/z3_brittle.txt`.  An earlier run of the same `main`
checkout (`/tmp/main.tsv`) had 67 failures: `lhospital` was `ok` there and
`nat_finite` failed.  The same checkout therefore has **66 deterministic
failures**; the other two are Z3 process/timeout effects, not proof regressions.
The groups below count the 68 rows of the fresh run and call out those two.

## Method

For every `fail` row I replayed the stored proof with a throwaway wrapper around
`holpy.kernel.theory.Theory._check_proof_item` (and around
`parser.parse_proof_rule` for parse failures).  The wrapper records the deepest
proof item whose check raised, so "first failing step" below is the stored rule
or macro that failed; when a macro expands, the nested primitive failure is
mentioned in the evidence.  The raw first-step dump is
`/tmp/diag_fresh.jsonl`; the TSV used for names/messages is `/tmp/lib.tsv`.
I then reproduced the representative failures individually with `/tmp/tb.py`
(traceback plus `Thm.equal_elim`/`Thm.can_prove` diffs), `/tmp/parsefail.py`
(first failing parse) and small direct parser/context probes.  Every cause below
says what was actually run; anything not reproduced is marked as a guess.

## Summary table (ordered by group size)

| # | Cause | Count | Exception type(s) | First failing step (rule/macro) |
|---:|---|---:|---|---|
| 1 | Printer drops parentheses around numeric `of_nat 0/1` or `-0` | 15 | `TypeInferenceException`, `CheckProofException`, `AssertionError` | `rewrite_goal`, `rewrite_fact`, `apply_theorem_for` |
| 2 | `apply_theorem[_for]` cannot instantiate a type variable that occurs only in the conclusion | 15 | `AssertionError` | `apply_theorem_for` (`finite_empty, {}`) |
| 3 | Unannotated overloaded `of_nat` under unary negation does not type-infer | 5 | `TypeInferenceException` | `rewrite_goal`, `apply_theorem_for` |
| 4 | Subproof `variable` declarations overwrite outer variable types in the parser context | 3 | `TypeInferenceException` | `intros`, `apply_fact`, `rewrite_goal_with_prev` |
| 5 | Stored equation/proof is eta-expanded; `equal_elim` compares syntactically | 3 | `InvalidDerivationException` | `rewrite_goal`, `rewrite_goal_with_prev` |
| 6 | Certificate is internally malformed (self-previous item or wrong local lemma) | 3 | `CheckProofException` | `apply_theorem`, `apply_theorem_for` |
| 7 | Theorem name is not available at that point (self-reference or defined later) | 3 | `TheoryException` | `intros`, `rewrite_goal` |
| 8 | `sum_eq` lost its `finite s` premise after the proof was recorded | 3 | `AssertionError` | `apply_theorem` (`sum_eq`) |
| 9 | `sum_lt`'s premise changed from an implication to a conjunction | 2 | `MatchException` | `apply_theorem` (`sum_lt`) |
| 10 | Theorem was renamed after the proof was recorded | 2 | `TheoryException` | `rewrite_goal`, `apply_theorem_for` |
| 11 | `disjE` certificate uses the first branch's implication as the second branch | 2 | `MatchException` | `apply_theorem` (`disjE`) |
| 12 | Stored statement differs from the derived statement only by bound-variable alpha-renaming | 2 | `CheckProofException` | `subproof` |
| 13 | `nat_const_ineq` mishandles real and negative numerals | 2 | `RecursionError`, `CheckProofException` | `nat_const_ineq` |
| 14 | `rewrite_goal[_with_prev]` rewrites to a form that does not match the stored previous item | 2 | `InvalidDerivationException` | `rewrite_goal`, `rewrite_goal_with_prev` |
| 15 | Z3 returns `unknown` / hits the 60 s timeout (known brittle theorems) | 2 | `AssertionError` | `z3` |
| 16 | `rewrite_goal` indexes an absent previous item | 1 | `IndexError` | `rewrite_goal` |
| 17 | Bound-variable capture: a lambda reuses a variable name that is free in the hypotheses | 1 | `InvalidDerivationException` | `rewrite_goal_with_prev` |
| 18 | Stored `intros` order is the reverse of the statement's implication order | 1 | `CheckProofException` | `intros` |
| 19 | `delete` arguments are swapped in the stored rewrite | 1 | `TypeInferenceException` | `rewrite_goal` |

The counts add up to **68**.

## 1. Printer drops parentheses around numeric `of_nat 0/1` or `-0` (15)

Theorems: `misc.abs_sqare_lt_1`, `real.{real_abs_pow, real_inv_neg,
real_pow_eq_1_imp}`, `realanalysis.reallim_null_neg`,
`realderivative.has_real_derivative_neg`,
`realintegral.{absolutely_real_integrable_0, has_real_measure_scaling_eq}`,
`transcendentals.{cos_bound, cos_eq_minus1, root_1, rpow_zero, sin_bound,
sin_eq_minus1}`, `trig_exp_log.exp_ge1`.

Examples (exact TSV error line, then first step):

| Theorem | Error line | First failing step |
|---|---|---|
| `real.real_abs_pow` | `TypeInferenceException: Unable to unify real with nat => ?'_t1` | `id=0 rule=rewrite_goal args='real_abs_nat, (abs::real ⇒ real) of_nat 1 = of_nat 1'` |
| `real.real_inv_neg` | `TypeInferenceException: Unable to unify real => real with real` | `id=0.3 rule=rewrite_goal args='real_neg_0, real_inverse -0 = -(real_inverse 0)'` |
| `misc.abs_sqare_lt_1` | `AssertionError: export: atom` | `id=2 rule=rewrite_goal args=('real_abs_nat', … < abs of_nat 1 …)` |

**Cause (verified).**  `pprint.helper` special-cases a number only for `0`, `1`
and `of_nat n` with `n >= 2`, while `get_priority_pair` treats every
`t.is_number()` as an atom priority.  Thus `of_nat 0` and `of_nat 1` are printed
without the parentheses their application form needs.  A direct round-trip
reproduction:

```text
abs ((of_nat::nat ⇒ real) 1)  -> prints '(abs::real => real) of_nat 1'
                              -> re-parse FAILS: Unable to unify real with nat => ?'_t0
abs ((of_nat::nat ⇒ real) 2)  -> prints '(abs::real => real) (of_nat 2)'  (ok)
real_inverse -0               -> parses as 'real_inverse - 0' (subtraction, not application)
```

`rpow_zero` is the same bug inside `... exp (y * log -0) ...`; the missing
parentheses make `log -0` a subtraction.  The `export: atom` failures go through
the same mis-parsed terms: the rewrite produces an atom proof term that cannot
be exported.  This is a live printer/parser bug, not merely stale text: a
re-save with the current printer reproduces it.  Fix the printer first, then
re-save the affected proofs.

## 2. Conclusion-only type variables in `apply_theorem[_for]` (15)

Theorems: `card.countable_sing`, `iterate.{finite_support_delta, iterate_empty,
iterate_pair, iterate_sing}`, `products.nproduct_sing`,
`set.{card_sing, finite_image_expand, finite_induct_strong, finite_sing,
finite_subset, has_size_natseg_lt, infinite_nonempty}`,
`sums.{nsum_sing, sum_sing}`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `set.finite_sing` | `AssertionError: apply_theorem: unmatched type variable ?'a` | `id=0 rule=apply_theorem_for args=('finite_empty', {})` |
| `iterate.finite_support_delta` | same | `id=0.1 rule=apply_theorem_for args=('finite_empty', {})` |
| `card.countable_sing` | same | `id=0 rule=apply_theorem_for args=('finite_empty', {})` |

**Cause (verified).**  `finite_empty` is `finite (∅::'a set)`: its only type
variable occurs in the conclusion and there is no premise to instantiate it.
`apply_theorem_macro` asserts that every type variable is in `inst.tyinst`
(`holpy/logic/logic.py`, around line 266), so the empty instantiation is
rejected.  This is the group fixed by `ft/tyinst-roundtrip-r2`: all 15 are `ok`
there.  No proof edit is needed once that branch lands.

## 3. Unannotated overloaded `of_nat` under unary negation (5)

Theorems: `floor.integer_cases`, `transcendentals.{cos_eq_1, sin_eq, sin_eq_1,
sin_zero_pi}`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `floor.integer_cases` | `TypeInferenceException: Unspecified type` | `id=1.2.7 rule=rewrite_goal args='real_neg_neg, --(of_nat n) = of_nat n'` |
| `transcendentals.sin_zero_pi` | `TypeInferenceException: Unspecified type` | `id=1.2.3 rule=apply_theorem_for args='eq_refl, {x: -(of_nat n1)}'` |
| `transcendentals.sin_eq_1` | `TypeInferenceException: Unspecified type` | `id=0.9.5.14 rule=apply_theorem_for args='exI, {P: …, a: -(of_nat (m + 1))}'` |

**Cause (verified first failure; fix choice is open).**  The stored terms leave
the result type of `of_nat` unconstrained inside unary minus.  Directly running
`parser.parse_term('-(of_nat (m + 1))')` and `parser.parse_term('--(of_nat m)')`
in the same context raises `TypeInferenceException: Unspecified type`.  This is
a parser/round-trip problem, not a changed theorem.  The likely fix is either to
print an explicit type for an ambiguous `of_nat` or to re-save these lines with
an explicit annotation; I have not chosen between them (small guess).

## 4. Subproof `variable` declarations overwrite outer variable types (3)

Theorems: `set.card_insert`, `iterate.iterate_reflect`,
`trig_series.power_series_derivative_shift`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `set.card_insert` | `TypeInferenceException: Unable to unify ?'_t0 set with nat` | `id=2.5 rule=intros th='finite s ⊢ ∀x::'a. ∀y. ∀s. …'` |
| `iterate.iterate_reflect` | `TypeInferenceException: Unable to unify ?'_t2 => ?'_t1 with nat` | `id=2.12 rule=apply_fact th='… iterate op ({m..n}) x = …'` |
| `trig_series.power_series_derivative_shift` | `TypeInferenceException: Unable to unify real with nat` | `id=15 rule=rewrite_goal_with_prev` |

**Cause (verified).**  `server.parse_proof` handles a `variable` line by writing
into the global `context.ctxt.vars` and never restores it when the subproof
ends.  In `iterate.iterate_reflect`, line `2.11.0 variable x, nat` changes the
outer theorem variable `x : nat ⇒ 'a` to `x : nat`; the next line using the
outer `x` then fails.  `trig_series` does the same at line `8.0`, and
`set.card_insert` at its `s, nat` declaration, shadowing the outer `s : 'a set`
used in the later `th`.  I confirmed the overwritten context directly (printing
`context.ctxt.vars` after replaying the preceding `variable` lines).  The
minimal fix is scoped variable declarations in `parse_proof`, not a library
edit; re-save after fixing if any stored `th` still contains the ambiguous name.

## 5. Eta-expanded stored equations (3)

Theorems: `logic_base.someI`, `logic_base.some_the`,
`sums.nsum_multicount_gen`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `logic_base.someI` | `InvalidDerivationException: equal_elim` | `id=3 rule=rewrite_goal args=('eq_sym_eq', (Some P) = (SOME x1. P x1))` |
| `logic_base.some_the` | `InvalidDerivationException: equal_elim` | `id=4 rule=rewrite_goal args=('eq_sym_eq', P (Some P) ⟷ P (SOME x. P x))` |
| `sums.nsum_multicount_gen` | `InvalidDerivationException: equal_elim` | `id=8 rule=rewrite_goal_with_prev` |

**Cause (verified).**  The patched `Thm.equal_elim` shows the two sides differ
only by eta: `Some P` versus `SOME x1. P x1`, or `nsum t k` versus
`nsum t (λi. k i)`.  `Thm.can_prove`/`equal_elim` compare terms syntactically
and `beta_norm` does not eta-reduce.  This needs a design decision (normalise
the library statements/proofs, or make the checker accept eta), so I did not
choose a fix.

## 6. Internally malformed certificates (3)

Theorems: `nat.nat_MAX`, `nat.div_le`, `gcd.gcd_le_min_eq`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `nat.nat_MAX` | `CheckProofException: id 0.7 cannot depend on 0.7` | `id=0.7 rule=apply_theorem args='conjD1'` (`prevs=['0.7']`) |
| `nat.div_le` | `CheckProofException: id 1.0 cannot depend on 1.0` | `id=1.0 rule=apply_theorem_for args=('division', {'m': m})` (`prevs=['1.0']`) |
| `gcd.gcd_le_min_eq` | `CheckProofException: output does not match` | `id=1.2.3.4 rule=apply_theorem args='conjI'` |

**Cause (verified).**  The first two stored items literally list themselves as
their own previous item; the checker correctly refuses.  In `gcd_le_min_eq`,
line `1.2.3.3` proves `n = 0 ⟶ n = 0` while the conjunction at `1.2.3.4`
expects `n = 0 ⟶ m = 0`, so `conjI` derives the wrong second conjunct (shown by
`Thm.can_prove`: got `(n = 0 --> n = 0)`, expected `(n = 0 --> m = 0)`).  These
are certificate defects; repair the three proofs or quarantine them under
decision 5.

## 7. Theorem name unavailable: self-reference or defined later (3)

Theorems: `logic_base.trivial`, `transcendentals.rpow_pos_le`,
`transcendentals.rpow_lt2`.

Examples:

| Theorem | Error line | First failing step |
|---|---|---|
| `logic_base.trivial` | `TheoryException: Theorem trivial not found` | `id=1 rule=intros args=[]` |
| `transcendentals.rpow_pos_le` | `TheoryException: Theorem rpow_zero not found` | `id=3.3 rule=rewrite_goal args=('rpow_zero', …)` |
| `transcendentals.rpow_lt2` | `TheoryException: Theorem rpow_zero not found` | `id=5.6 rule=rewrite_goal args=('rpow_zero', …)` |

**Cause (verified).**  `intros_macro` with one previous item calls
`apply_theorem('trivial', pt)` (`holpy/logic/logic.py` around line 208); the
proof of `logic_base.trivial` therefore needs the theorem it is proving.  In
`transcendentals.json`, `rpow_pos_le` (index 317) and `rpow_lt2` (index 318)
come before `rpow_zero` (index 320), although the stored proofs use it; commit
`97823dd9` reordered `rpow_zero` after them.  `trivial` needs re-proof (or its
proof dropped), and `rpow_zero` should be moved before its users (or the two
proofs reordered).

## 8. `sum_eq` lost its `finite s` premise (3)

Theorems: `sums.sum_restrict`, `sums.sum_eq_superset`,
`sums.sum_multicount_gen`.

| Theorem | Error line | First failing step |
|---|---|---|
| `sums.sum_restrict` | `AssertionError: apply_theorem: too many prevs.` | `id=2 rule=apply_theorem args='sum_eq'` |
| `sums.sum_eq_superset` | same | `id=5 rule=apply_theorem args='sum_eq'` |
| `sums.sum_multicount_gen` | same | `id=4 rule=apply_theorem args='sum_eq'` |

**Cause (verified).**  `git show 47ce6eb1 -- library/iterate.json` removes
`finite s ⟶` from `sum_eq`'s statement.  The three stored applications still
pass the now-extra `finite s` fact, so `apply_theorem` sees one too many
prevs.  Local proof edits (drop that prev and use it in the surrounding
`intros`) are enough.

## 9. `sum_lt`'s premise changed from implication to conjunction (2)

Theorems: `sums.sum_lt_all`, `sums.sum_pos_lt`.

| Theorem | Error line | First failing step |
|---|---|---|
| `sums.sum_lt_all` | `MatchException: When matching conj with implies` | `id=5 rule=apply_theorem args='sum_lt'` |
| `sums.sum_pos_lt` | same | `id=5 rule=apply_theorem args='sum_lt'` |

**Cause (verified).**  `git show 722d4dc6` changes the third premise of
`sum_lt` from `∃x. x ∈ s ⟶ f x < g x` to `∃x. x ∈ s ∧ f x < g x`.  The stored
`z3` steps still prove the implication form, so matching the conjunction fails.
Re-prove the `z3` line (and the surrounding goal) in each theorem.

## 10. Theorem renamed after the proof was recorded (2)

Theorems: `prime.finite_exp_le`, `sums.sum_abs_le`.

| Theorem | Error line | First failing step |
|---|---|---|
| `prime.finite_exp_le` | `TheoryException: Theorem member_numseg not found` | `id=3 rule=rewrite_goal args=('member_numseg', …)` |
| `sums.sum_abs_le` | `TheoryException: Theorem sub_abs not found` | `id=2 rule=apply_theorem_for args=('sub_abs', {'f': f, 's': s})` |

**Cause (verified).**  `git show 0d6e9eef -- library/iterate.json` renames
`member_numseg` to `member_natseg`; `47ce6eb1` renames `sub_abs` to `sum_abs`.
The current library has only the new names.  Both are one-line proof edits.

## 11. `disjE` uses the first branch's implication for both branches (2)

Theorems: `prime.distinct_prime_coprime`, `realanalysis.reallim_unique`.

| Theorem | Error line | First failing step |
|---|---|---|
| `prime.distinct_prime_coprime` | `MatchException: When matching ?B with d = 1` | `id=5.1.6.4 rule=apply_theorem args='disjE'` |
| `realanalysis.reallim_unique` | `MatchException: When matching ?B with trivial_limit net` | `id=5.7.2 rule=apply_theorem args='disjE'` |

**Cause (verified by reading the stored lines and rerunning).**  In
`distinct_prime_coprime`, the disjunction is `d = 1 ∨ d = q`, but the second
and third `disjE` prevs are both `d = 1 ⟶ d = 1` (`5.1.5` and `5.1.6.3`); the
third branch needs `d = q ⟶ d = 1`.  `reallim_unique` has the same shape: both
branch implications are `trivial_limit net ⟶ trivial_limit net` (`5.6` and
`5.7.1`).  Matcher traces end with `When matching ?B with d = 1` /
`trivial_limit net`.  Repair the branch proof in each certificate.

## 12. Bound-variable alpha-renaming only (2)

Theorems: `prime.coprime_rexp`, `transcendentals.real_root_pow_gen`.

| Theorem | Error line | First failing step |
|---|---|---|
| `prime.coprime_rexp` | `CheckProofException: output does not match` | `id=4 rule=subproof` |
| `transcendentals.real_root_pow_gen` | `CheckProofException: output does not match` | `id=2 rule=subproof` |

**Cause (verified).**  `Thm.can_prove` shows the two terms are identical up to
the bound variable name: stored `!n1. …` vs derived `!n. …` (and the same for
`real_root_pow_gen`).  `can_prove` is syntactic and does not alpha-convert.
Either re-save the stored `th` with the derived bound name or make the checker
alpha-aware; re-saving is the smaller change (but needs a round-trip check
after the printer fixes).

## 13. `nat_const_ineq` mishandles real and negative numerals (2)

Theorems: `transcendentals.sin_pimul_eq_0`, `transcendentals.tan_pi4`.

| Theorem | Error line | First failing step |
|---|---|---|
| `transcendentals.sin_pimul_eq_0` | `RecursionError: maximum recursion depth exceeded` | `id=0.3.4 rule=nat_const_ineq args=¬(-(1::real) = 0)` |
| `transcendentals.tan_pi4` | `CheckProofException: output does not match` | `id=1 rule=nat_const_ineq args=¬((2::real) = 0)` |

**Cause (verified; genuine macro bug).**  `holpy/data/nat.py` builds the proof
with `Binary(n // 2)`.  For the negative numeral in `sin_pimul_eq_0`, the
recursion never reaches a base case:
`File ".../holpy/data/nat.py", line 575, in ineq_zero_proof_term ... Binary(n // 2)`.
For `tan_pi4`, the macro's proof rewrites the real numeral to a nat numeral:
expected `~((2::real) = 0)`, derived `~((2::nat) = 0)`.  `can_eval` only checks
`is_number()`, not that the numeral is a non-negative nat.  This is a macro fix,
not a proof edit.

## 14. `rewrite_goal[_with_prev]` no longer matches the stored prev (2)

Theorems: `gcd.divides_cases`, `iterate.iterate_closed`.

| Theorem | Error line | First failing step |
|---|---|---|
| `gcd.divides_cases` | `InvalidDerivationException: equal_elim` | `id=7 rule=rewrite_goal_with_prev args='m = 0 ∨ m = n ∨ 2 * n ≤ m'` |
| `iterate.iterate_closed` | `InvalidDerivationException: equal_elim` | `id=3.4 rule=rewrite_goal args=('if_P', P (if … then … else …))` |

**Cause (verified first failure; root is a certificate/macro mismatch).**  The
patched `equal_elim` prints the two sides.  In `divides_cases`, the left side
contains `m = n * 1` while the stored prev `6` is the implication
`m = n * k ⟶ …`; the `rewrite_goal_with_prev` prev list `[1, 6]` is not the
goal that the rewrite produces.  In `iterate_closed`, the rewrite produces
`P (iterate …) ⟷ P (if …)`, but prev `3.3` is
`(∀x. …) ⟶ P (iterate …)`, not the goal.  Both look like stale/incorrect prev
lists rather than a wrong theorem; re-proof or repair the prevs.  I did not
determine which of the two is the intended certificate — this is the one cause
where "stale prev list" is a best-supported hypothesis, not a proven root.

## 15. Z3 `unknown` / 60 s timeout (2, known brittle)

Theorems: `realderivative.lhospital`, `set.nat_finite`.

| Theorem | Error line | First failing step |
|---|---|---|
| `realderivative.lhospital` | `AssertionError: Z3: not solved.` | `id=14.3 rule=z3` |
| `set.nat_finite` | `AssertionError: Z3: not solved.` | `id=0.2.5 rule=z3` |

**Cause (verified).**  Both theorems are explicitly listed as brittle in
`scripts/z3_brittle.txt`.  `lhospital` failed at the `z3` step `14.3` after
61.08 s in the fresh run, while the previous run of the same checkout checked it
in 1.77 s; `nat_finite` failed at `0.2.5` after 60.44 s and checked in 0.61 s
on the TyInst branch.  Because the standalone diagnostic happened to check
`lhospital` successfully, I pinned its step with a targeted
`process_theory('realderivative')` replay (`/tmp/lh_step.py`) that logs every
non-`True` Z3 answer: it printed `SOLVE_FAIL at step 14.3 z3`, then
`CHECK_FAIL at step 14.3 ... AssertionError Z3: not solved.`  This is a
solver/process effect, not a proof regression.  Pinning the tested Z3 version or
replacing the two quantifier-heavy `z3` lines with explicit witnesses would
remove the flakiness; no library statement change is needed.

## 16. `rewrite_goal` indexes an absent previous item (1)

Theorem: `realintegral.has_real_measure`.

| Error line | First failing step |
|---|---|
| `IndexError: tuple index out of range` | `id=0 rule=rewrite_goal args=('has_real_integral_restrict_univ', …)` (`prevs=[]`) |

**Cause (verified).**  The traceback ends at `holpy/logic/logic.py:477`,
`pt = pt.equal_elim(pts[0])`, with `pts` empty.  The stored `rewrite_goal` line
has no previous item; the macro handles the reflexive case but not this
non-reflexive zero-prev case.  Either the certificate needs the missing goal
prev or `rewrite_goal` must handle this case.  I did not decide which is
intended (small guess; likely a stale certificate because every other
`rewrite_goal` line in the library carries its goal prev).

## 17. Bound-variable capture in a lambda (1)

Theorem: `realderivative.real_derivative_ivt_increasing`.

| Error line | First failing step |
|---|---|
| `InvalidDerivationException: abstraction: variable occurs in assmptions` | `id=2.4.2.2.22.3.17 rule=rewrite_goal_with_prev` |

**Cause (verified via traceback; fix is a guess).**  The stored goal contains
`λx. f x - t * x` while the hypotheses already contain a free variable `x`.
During `rewrite_goal_with_prev`, conversion abstracts over the lambda variable
`x`, and `Thm.abstraction` rejects it because that variable name occurs in the
assumptions.  The clean fix is either alpha-renaming the lambda bound variable
in the certificate or making conversion capture-avoiding; the traceback alone
does not tell which the original author intended.

## 18. Stored `intros` order is reversed (1)

Theorem: `set.card_image_inj`.

| Error line | First failing step |
|---|---|
| `CheckProofException: output does not match` | `id=4 rule=intros args=[]` |

**Cause (verified).**  `Thm.can_prove` prints the statement
`(∀x. ∀y. …) ⟶ finite s ⟶ card …` but the derived statement is
`finite s ⟶ (∀x. ∀y. …) ⟶ card …`; the stored proof introduces `finite s`
first.  The theorem is not false, the certificate's intro order is wrong.
Re-proof or reorder the `intros` items.

## 19. `delete` arguments are swapped (1)

Theorem: `set.member_delete`.

| Error line | First failing step |
|---|---|
| `TypeInferenceException: Unable to unify ?'_t2 set with 'a` | `id=1 rule=rewrite_goal args='delete_def, y ∈ delete x A ⟷ ¬(y = x) ∧ y ∈ A'` |

**Cause (verified).**  The current definition is `delete A x = {y. …}` (see
`delete_def`), but the stored rewrite writes `delete x A`.  Swapping `x` and
`A` in the stored `args`/`th` makes the line parse.

## Proposed fix order

1. **Land `ft/tyinst-roundtrip-r2` (#45).**  Removes all 15 group-2 failures
   with no proof searching; this is already the measured 68 → 52 change.
2. **Fix the printer's numeric parenthesisation (group 1, 15).**  Extend the
   `helper`/`get_priority_pair` Number special case so `of_nat 0/1` and negative
   numerals are printed as applications, add a print/re-parse test over all
   stored `args`/`th`, then re-save the affected proofs.  Re-saving before this
   fix would recreate the bad strings.
3. **Fix parser context scoping (group 4, 3) and the ambiguous `of_nat` under
   negation (group 3, 5).**  The scoping fix is in `server.parse_proof`; the
   `of_nat` cases need one parser/printing policy decision.  This is the same
   round-trip area as group 1 and is best done together.
4. **Do the mechanical certificate repairs:** renamed theorems (group 10, 2),
   `sum_eq` prevs (group 8, 3), `sum_lt` premise (group 9, 2), `disjE` branches
   (group 11, 2), alpha-renamed `th` strings (group 12, 2), malformed
   self-previous/wrong-trivial certificates (group 6, 3), and the `trivial` /
   `rpow_zero` ordering problems (group 7, 3).  These are local edits and do not
   need new proof search (except `trivial`, which needs a real proof or a
   decision to keep it axiomatic, and the `rpow_zero` order move).
5. **Fix the macro/logic defects:** `nat_const_ineq` (group 13, 2),
   `rewrite_goal[_with_prev]` prev handling (group 14, 2),
   `rewrite_goal` zero-prev `IndexError` (group 16, 1), and capture-avoiding
   abstraction (group 17, 1).  Groups 13 and 16 are code bugs; groups 14 and 17
   first need a decision on whether to repair the certificate or the macro.
6. **Decide eta handling (group 5, 3).**  This is a library-normalisation or
   checker-equality decision, not a mechanical repair.
7. **Handle Z3 brittleness last (group 15, 2).**  It is already documented in
   `scripts/z3_brittle.txt`; either pin the solver used for the release check or
   replace the two hard `z3` lines.

## Found, not fixed

- `docs/library_check.tsv` in this checkout is stale (107 `fail` rows) compared
  with a fresh run on the same commit (66 deterministic failures).  I did not
  regenerate it because this task is report-only.
- Earlier triage reports (`failures_a.md`, `failures_b.md`) blamed broad
  `TypeInferenceException`/macro changes for many failures.  The fresh first-step
  trace shows that most of those are either the printer bug (group 1), the
  parser-context shadowing bug (group 4), or already-fixed type-variable cases
  (group 2); their classifications should not be used as-is.
- `realderivative.lhospital` and `set.nat_finite` make the fail count depend on
  process history/CPU load even with `--jobs 2`.  Comparisons must keep using
  `--allow-degraded scripts/z3_brittle.txt` (or an updated equivalent).

## Questions for Alex

1. Printer fix: extend the Number special case to `0`/`1` (changes how a bare
   `of_nat 1` prints) or stop treating `of_nat 0/1` as atom priority (smaller
   blast radius)?  Both make group 1 round-trip.
2. Eta (group 5): normalise the three library statements/proofs, or make
   `can_prove`/`equal_elim` accept eta-equivalence?
3. For the six certificate-defect theorems (groups 6, 16, 17), do you prefer
   re-proof/manual repair or the decision-5 quarantine (`sorry` + index)?
4. For `logic_base.trivial`, re-prove it without `intros`, or drop its proof and
   keep it axiomatic as it was before 2020?

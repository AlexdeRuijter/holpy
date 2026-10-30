> **Status: unverified leads.** Written by a VM agent from the 2026-10-30 library baseline (z3-solver 5.3.2). Causes and "fix size" estimates have not been checked by a human; a sibling triage report was wrong in places. Use as a starting point only.

# Triage C: `set`, `real`, `sums`, `logic_base`

Scope: the 32 failing theorems of these four theories in
`docs/library_check.tsv` (status `fail`, column 3).  Baseline rows:

| Theory | ok | fail | gaps | noproof |
|---|---:|---:|---:|---:|
| `logic_base` | 33 | 3 | 0 | 0 |
| `set` | 81 | 10 | 4 | 1 |
| `sums` | 187 | 9 | 0 | 0 |
| `real` | 203 | 10 | 3 | 118 |

No file under `holpy/` was changed by this task.  Reproduction command:

```bash
PYTHONPATH=. python scripts/check_library.py logic_base set sums real --jobs 1 \
    --out /tmp/c.tsv
```

The first failing proof step was obtained with a throwaway script under `/tmp`
(not committed) that copies the loading loop of `scripts/check_library.py`,
installs a wrapper around `Theory._check_proof_item` recording
`(seq.id, seq.rule, seq.args)` while the exception propagates, and calls
`server.parse_proof` (which itself runs `check_proof`).  For parse failures the
wrapper was around `parser.parse_proof_rule`.  Commands and outputs are quoted
in the evidence sections.

## Summary table

The counts add up to 32.  "First step" is the first stored proof line that
fails; for a macro whose expansion fails, the nested generated line is shown
after `->`.

| Cause | Count | Example |
|---|---:|---|
| `genuine-kernel-or-logic-bug`: `rewr_conv`/`matcher` accept an ill-typed bare-variable match, then `Thm.substitution` fails | 6 | `real.real_inv_eq_0` |
| `genuine-kernel-or-logic-bug`: the printer loses the parentheses around a numeric `of_nat 0/1` argument (`get_priority_pair` calls it an atom, but `helper` prints it as an application) | 2 | `real.real_abs_pow` |
| `stale-proof`: `f8e0462a` rewrote one proof string without the parentheses the current printer emits | 1 | `real.real_inv_neg` |
| `stale-proof`: stored terms are eta-expanded relative to the terms the proof derives | 3 | `logic_base.someI` |
| `stale-proof`: recorded certificate is internally inconsistent and has never checked (four different defects) | 4 | `set.member_delete` |
| `missing-or-changed-macro/API`: `apply_theorem[_for]` cannot apply a theorem whose only type variable is in the conclusion | 9 | `set.finite_sing` |
| `library-statement-changed`: `sum_lt`'s third premise changed from `∃x. x ∈ s ⟶ ...` to `∃x. x ∈ s ∧ ...` | 2 | `sums.sum_lt_all` |
| `library-statement-changed`: `sum_eq` lost its `finite s` premise | 3 | `sums.sum_restrict` |
| `library-statement-changed`: `sub_abs` was renamed to `sum_abs` | 1 | `sums.sum_abs_le` |
| `z3-version/timeout`: Z3 returns `unknown` | 1 | `real.real_down` |

## Group 1 — genuine logic bug in `rewr_conv`/`matcher` (6)

Theorems:

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `real.real_inv_eq_0` | `InvalidDerivationException: substitution` | `id=0.4, rule=rewrite_goal_sym, args=('real_inv_inv', 'x = 0')` | high | one small fix in `conv.py`/`matcher.py`, then all 6 pass |
| `real.real_lt_inv_eq` | same | `id=0.4, rule=rewrite_goal_sym, args=('real_inv_inv', '0 < x')` | high | same |
| `real.real_pow2_abs` | same | `id=1.2, rule=rewrite_goal_sym, args=('mult_1_right', 'even 2')` | high | same |
| `real.real_pow_mono_inv` | same | `id=4.9, rule=rewrite_goal_sym, args=('real_inv_inv', 'x ^ m ≤ x ^ n')` | high | same |
| `real.real_arch_pow_inv` | same | `id=2.9, rule=rewrite_goal_sym, args=('real_inv_inv', 'x ^ n < y')` | high | same |
| `real.real_eq_sgn_abs` | same | `id=1.5, rule=rewrite_goal_sym, args=('real_sgn_abs', 'x = y')` | high | same |

**Evidence.**  The traceback ends in `holpy/logic/conv.py`:

```text
File "/home/agent/work/AlexdeRuijter__holpy/holpy/logic/conv.py", line 385, in get_proof_term
    pt = pt.substitution(inst)
File "/home/agent/work/AlexdeRuijter__holpy/holpy/kernel/thm.py", line 293, in substitution
    raise InvalidDerivationException("substitution")
```

`rewr_conv` matches the right-hand side of the equation (a bare variable) against
the *whole* current term, without checking types.  For `real_inv_inv`
(`real_inverse (real_inverse x) = x`, used with `sym`) it matches `x` against
the boolean term `real_inverse (real_inverse x) = real_inverse (real_inverse 0)`
and then tries to substitute a boolean for a real variable.  A throwaway
wrapper that converts that `InvalidDerivationException` into a `ConvException`
(so `try_conv`/`top_sweep_conv` simply skip the ill-typed top-level match and
descend) makes all six certificates check:

```text
$ for t in real_inv_eq_0 real_lt_inv_eq real_pow2_abs real_pow_mono_inv \
           real_arch_pow_inv real_eq_sgn_abs; do
    PYTHONPATH=. python /tmp/convfix.py real $t; done
==> real_inv_eq_0        CHECK OK
==> real_lt_inv_eq       CHECK OK
==> real_pow2_abs        CHECK OK
==> real_pow_mono_inv    CHECK OK
==> real_arch_pow_inv    CHECK OK
==> real_eq_sgn_abs      CHECK OK
```

The same theorem fails identically in pre-restructure code (`f043f6a0^`),
so this is **not** a regression introduced by this fork:

```text
$ cd /tmp/repopre && PYTHONPATH=/tmp/repopre python /tmp/diag_old.py real real_inv_eq_0
EXC: InvalidDerivationException substitution
  id=0.4 rule=rewrite_goal_sym args=('real_inv_inv', Comb(...)) -> InvalidDerivationException: substitution
```

Fix: a one-line-ish change in the trusted *logic* layer (either a type check
for bare `SVar` patterns in `matcher.first_order_match`, or catching the
ill-typed substitution in `rewr_conv`), plus a regression test.  The proofs
themselves need no change.  This is not a kernel bug: the kernel correctly
rejects the ill-typed substitution.

## Group 2 — printer loses the parentheses around numeric `of_nat 0/1` (2)

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `real.real_abs_pow` | `TypeInferenceException: Unable to unify real with nat => ?'_t1` (parse) | `id=0, rule=rewrite_goal, args='real_abs_nat, (abs::real ⇒ real) of_nat 1 = of_nat 1'` | high | one line in the printer + re-save this proof |
| `real.real_pow_eq_1_imp` | `CheckProofException: output does not match` | `id=4, rule=apply_theorem, args='real_pow_eq_abs'` (the stored `th` of id 4) | high | one line in the printer + re-save this proof |

**Evidence.**  This is a live printer bug, not only an old string.  The printer
special-cases a numeric `of_nat n` only for `n >= 2` in `helper`, but
`get_priority_pair` uses `t.is_number()`, which is true for `of_nat 0` and
`of_nat 1`.  Those two therefore get atom priority and lose the parentheses
that their *printed* form (a function application) needs:

```text
$ PYTHONPATH=. python -c "... parser.parse_term('(abs::real ⇒ real) (of_nat n)') ..."
0 arg.is_number True dest 0 | printed '(abs::real ⇒ real) of_nat 0' | roundtrip parse fails TypeInferenceException
1 arg.is_number True dest 1 | printed '(abs::real ⇒ real) of_nat 1' | roundtrip parse fails TypeInferenceException
2 arg.is_number False dest None | printed '(abs::real ⇒ real) (of_nat 2)' | roundtrip True
3 arg.is_number False dest None | printed '(abs::real ⇒ real) (of_nat 3)' | roundtrip True
```

The stored strings come from the same missing-parenthesis printer output (the
`real_pow_eq_1_imp` string predates the type annotation, but has the same
unparenthesised `of_nat 1`):

```text
$ git show f8e0462a -- library/real.json
-                    "args": "real_abs_nat, abs ((of_nat::nat ⇒ real) 1) = of_nat 1"
+                    "args": "real_abs_nat, (abs::real ⇒ real) of_nat 1 = of_nat 1"
...
-                    "th": "¬(n = 0), x ^ n = 1 ⊢ abs x = abs (of_nat 1)"
+                    "th": "¬(n = 0), x ^ n = 1 ⊢ abs x = abs of_nat 1"
```

The current parser parses `(abs::real ⇒ real) of_nat 1` as `((abs) of_nat) 1`
and `abs of_nat 1` as `(abs of_nat) 1`:

```text
$ PYTHONPATH=. python /tmp/parsefail.py real real_abs_pow
PARSE_PROOF_RULE FAIL at id=0 rule=rewrite_goal args='real_abs_nat, (abs::real ⇒ real) of_nat 1 = of_nat 1'
  -> TypeInferenceException Unable to unify real with nat => ?'_1
```

Fixing only the stored strings is not sufficient: a re-save would reproduce the
bad string for `of_nat 0/1`.  Fix: one line in `holpy/syntax/pprint.py`
(parenthesise the argument as an application, or extend the `Number`
special-case to 0 and 1 consistently) and then re-save these two proofs.
Classification: `genuine-kernel-or-logic-bug` (printer, not kernel).

## Group 2b — stale string from `f8e0462a` (1)

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `real.real_inv_neg` | `TypeInferenceException: Unable to unify real => real with real` (parse) | `id=0.3, rule=rewrite_goal, args='real_neg_0, real_inverse -0 = -(real_inverse 0)'` | high | one line (restore the parentheses) |

**Evidence.**  `f8e0462a` rewrote the stored line without the parentheses:

```text
$ git show f8e0462a -- library/real.json
-                    "args": "real_neg_0, real_inverse (-0) = -(real_inverse 0)"
+                    "args": "real_neg_0, real_inverse -0 = -(real_inverse 0)"
```

The unparenthesised text parses as a binary minus between `real_inverse` and
`0`, and the current printer now correctly prints the intended term with
parentheses:

```text
$ PYTHONPATH=. python /tmp/parsefail.py real real_inv_neg
PARSE_PROOF_RULE FAIL at id=0.3 rule=rewrite_goal args='real_neg_0, real_inverse -0 = -(real_inverse 0)'
  -> TypeInferenceException Unable to unify real => real with real

$ PYTHONPATH=. python -c "... print parser.parse_term('real_inverse (-0)') ..."
real_inverse (-0)          # re-parses to the right term
```

Classification: `stale-proof` (the stored text no longer round-trips).  Fix: add
the parentheses back in the stored `args`/`th` of id 0.3.

## Group 3 — stale eta-expanded stored terms (3)

Theorems:

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `logic_base.someI` | `InvalidDerivationException: equal_elim` | `id=3, rule=rewrite_goal, args='eq_sym_eq, (Some P) = (SOME x1. P x1)'` | high | one theorem re-proof (or normalise the eta-expanded strings) |
| `logic_base.some_the` | same | `id=4, rule=rewrite_goal, args='eq_sym_eq, P (Some P) ⟷ P (SOME x. P x)'` | high | same |
| `sums.nsum_multicount_gen` | same | `id=8, rule=rewrite_goal_with_prev, args='nsum s (λx. nsum ({j. j ∈ t ∧ R x j}) (λj. 1)) = nsum t (λi. k i)'` | medium-high | same |

**Evidence.**  In `someI` the rewrite result differs only by eta:

```text
EQUAL_ELIM FAIL
self.prop : (SOME x1. P x1) = (Some P) <--> (Some P) = (SOME x1. P x1)
arg.prop  : (SOME x1. P x1) = (SOME x1. P x1)
```

`Some P` (the `some_AX` statement) and `SOME x1. P x1` (parsed as
`Some (λx1. P x1)`) are eta-equivalent but not syntactically equal;
`beta_norm` does not eta-reduce, and `Thm.can_prove`/`equal_elim` compare
syntactically.

For `nsum_multicount_gen` the same difference appears in the `equal_elim`
comparison:

```text
DIFF ty at .arg.arg 4 1
```

(the left side has `Abs(i, 'b, ...)`, the right side the bare `Var(k, ...)`:
`nsum t (λi. k i)` versus `nsum t k`).  The theorem statement itself is stored
eta-expanded (`... = nsum t (λi. k i)`), so this is a statement/proof
normalisation mismatch rather than a changed definition.  `someI` and
`some_the` also fail identically in pre-restructure code (`a14b6524^` for
`someI`, `f043f6a0^` for `some_the`), so this is old, not a regression from
this branch.  Fix: re-prove with eta-normalised terms, or
normalise/eta-convert the stored statement+proof (needs Alex' decision because
it changes either the library statement or the checker's equality).

## Group 4 — stale certificates that never checked (4)

These four defects differ, but they share the cause: the certificate was
recorded from an interactive session and was never replayed through the
certificate checker before the WS0 baseline.

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `logic_base.trivial` | `TheoryException: Theorem trivial not found` | `id=1, rule=intros, args=''` (prevs `['0']`) | high | one theorem re-proof, or drop the proof (restore the old axiom) |
| `set.member_delete` | `TypeInferenceException: Unable to unify ?'_t2 set with 'a` (parse) | `id=1, rule=rewrite_goal, args='delete_def, y ∈ delete x A ⟷ ¬(y = x) ∧ y ∈ A'` | high | one line (swap `x` and `A` in args and `th`) |
| `set.card_insert` | `TypeInferenceException: Unable to unify ?'_t0 set with nat` (parse) | `id=2.5, rule=intros, args=''` (prevs `2.0`–`2.4`) | high | one theorem re-proof / automatic re-save (rename the shadowed bound variable) |
| `set.card_image_inj` | `CheckProofException: output does not match` | `id=4, rule=intros, args=''` (prevs `['0','3']`) | high | one theorem re-proof (restore the `revert_intro`/implication order) |

**`trivial`.**  `intros_macro` implements its one-prev case as
`return apply_theorem('trivial', pt)` (`holpy/logic/logic.py:208-209`), so the
theorem `trivial` cannot be proved by `intros` before `trivial` exists.  There
is no earlier `trivial` in the theory:

```text
$ PYTHONPATH=. python /tmp/firststep.py logic_base trivial
### logic_base.trivial (item 33)
EXC: TheoryException | Theorem trivial not found
CHAIN outermost-first:
   id=1 rule=intros args=[] -> TheoryException: Theorem trivial not found
```

Git history confirms the proof was added *after* `trivial` had been an axiom:
`git log -S'"name": "trivial"' -- library/logic_base.json` shows
`70d4078b` (2019) added it without a proof and `a9db98b8` (2020-11-01)
added the four-line proof.  The self-reference is the direct cause.

**`member_delete`.**  `delete` is defined as
`'a set ⇒ 'a ⇒ 'a set`, `delete A x = {y. ¬(y = x) ∧ y ∈ A}`, while the
stored line writes `delete x A`:

```text
$ PYTHONPATH=. python /tmp/parsefail.py set member_delete
PARSE_PROOF_RULE FAIL at id=1 rule=rewrite_goal args='delete_def, y ∈ delete x A ⟷ ¬(y = x) ∧ y ∈ A'
  -> TypeInferenceException Unable to unify ?'_t2 set with 'a
```

The wrong argument order is present already in the commit that introduced the
theorem (`3cdebce2`, 2020-04-29).

**`card_insert`.**  The subproof introduces a variable `s :: nat` that shadows
the theorem variable `s :: 'a set`, and the stored `th` of `2.5` uses the same
printed name for both:

```text
th = "finite s ⊢ ∀x::'a. ∀y. ∀s. ¬(x = y) ⟶ Suc (Suc s) = Suc (Suc s)"
```

Reparsing gives `s` type `'a set` in `finite s` and `nat` in `∀s`, hence:

```text
$ PYTHONPATH=. python /tmp/parsefail.py set card_insert
PARSE_PROOF_RULE FAIL at id=2.5 rule=intros args='' th="finite s ⊢ ∀x::'a. ∀y. ∀s. ¬(x = y) ⟶ Suc (Suc s) = Suc (Suc s)"
  -> TypeInferenceException Unable to unify ?'_t0 set with nat
```

It fails identically at `9ba68c40` (the commit that added the proof), so this is
not a new printer regression; the printed certificate was ambiguous from the
start.

**`card_image_inj`.**  The statement is
`(∀x. …) ⟶ finite s ⟶ card (image f s) = card s`, but the final `intros`
introduces `finite s` first:

```text
$ PYTHONPATH=. python /tmp/fullcheck.py set card_image_inj
EXC: CheckProofException
output does not match
|- (!x. !y. x Mem s --> y Mem s --> f x = f y --> x = y) --> finite s --> card (image f s) = card s
 vs.
|- finite s --> (!x. !y. x Mem s --> y Mem s --> f x = f y --> x = y) --> card (image f s) = card s
```

The `steps` list starts with a `revert_intro` step that is not represented in
the stored proof.  Same result in pre-restructure code (`f043f6a0^`).

## Group 5 — `apply_theorem` cannot instantiate a conclusion-only type variable (9)

Theorems:

| Theory | Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|---|
| `set` | `finite_induct_strong` | `AssertionError: apply_theorem: unmatched type variable ?'a` | `id=3.2, rule=apply_theorem_for, args=('finite_empty', {})` (inside subproof `id=3`) | high | needs Alex: macro capability; not a one-line proof fix |
| `set` | `finite_subset` | same | `id=3.4, rule=apply_theorem_for, args=('finite_empty', {})` (inside `id=3`) | high | same |
| `set` | `finite_sing` | same | `id=0, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |
| `set` | `finite_image_expand` | same | `id=2, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |
| `set` | `infinite_nonempty` | same | `id=2.1, rule=apply_theorem_for, args=('finite_empty', {})` (inside `id=2`) | high | same |
| `set` | `card_sing` | same | `id=0, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |
| `set` | `has_size_natseg_lt` | same | `id=0, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |
| `sums` | `nsum_sing` | same | `id=0, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |
| `sums` | `sum_sing` | same | `id=0, rule=apply_theorem_for, args=('finite_empty', {})` | high | same |

**Evidence.**  `finite_empty` is a rule of the inductive predicate `finite`,
with a type variable only in its conclusion:

```text
$ python -c "import json; ... print(item['name'], item['prop'])"
finite_empty | finite (∅::'a set)
```

`apply_theorem_macro` matches premises (there are none here) with an empty
`Inst`, then asserts that every type variable of the theorem is in
`inst.tyinst`:

```text
holpy/logic/logic.py:264  # Check that all type variables are instantiated
holpy/logic/logic.py:266  assert stvar.name in inst.tyinst, \
                              "apply_theorem: unmatched type variable %s" % stvar
```

```text
$ PYTHONPATH=. python /tmp/firststep.py set finite_sing
### set.finite_sing (item 67)
EXC: AssertionError | apply_theorem: unmatched type variable ?'a
CHAIN outermost-first:
   id=0 rule=apply_theorem_for args=('finite_empty', {}) -> AssertionError: apply_theorem: unmatched type variable ?'a
```

Every one of the seven occurrences of `"finite_empty, {}"` in `set.json` (and
the two in `sums.json`) is in this list; there is no passing counterexample.
The certificates are logically sensible: applying the polymorphic rule and
keeping `'a` schematic.  The macro has no way to express that (it generalises
only term variables, `remain_svars`, not type variables), so this is a
**missing macro capability**, not a changed definition or a false theorem.
These proofs also fail in pre-restructure code (`f043f6a0^`,
`apply_theorem: unmatched type variables.`), so they were already uncheckable
before this branch.  Fix: decide
whether `apply_theorem[_for]` should leave a conclusion-only type variable
schematic (and generalise it), or whether the library should use a different
certificate.  That is a macro/API decision for Alex.

## Group 6 — `sum_lt`'s third premise changed after the proofs were recorded (2)

Theorems:

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `sums.sum_lt_all` | `MatchException: When matching conj with implies` | `id=5, rule=apply_theorem, args='sum_lt'` (prevs `0,3,4`) | high | one theorem re-proof / adapt the z3 step |
| `sums.sum_pos_lt` | same | `id=5, rule=apply_theorem, args='sum_lt'` (prevs `0,1,2`) | high | same |

**Evidence.**  Before `722d4dc6` (2020-05-07) `sum_lt` was

```text
finite s ⟶ (∀x. x ∈ s ⟶ f x ≤ g x) ⟶ (∃x. x ∈ s ⟶ f x < g x) ⟶ sum s f < sum s g
```

and from `722d4dc6` on it is

```text
finite s ⟶ (∀x. x ∈ s ⟶ f x ≤ g x) ⟶ (∃x. x ∈ s ∧ f x < g x) ⟶ sum s f < sum s g
```

The proofs still contain a `z3` line proving the implication form
(`∃x. x ∈ s ⟶ f x < g x`), so matching the conjunction premise fails.  Checking
the same library at the two commits (old checkout in `/tmp`):

```text
$ cd /tmp/repo0a2 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_lt_all
CHECK OK
$ cd /tmp/repo0a2 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_pos_lt
CHECK OK

$ cd /tmp/repo722 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_lt_all
EXC MatchException | [(Comb(Const(exists, ...), Abs(x, ..., Comb(Comb(Const(conj, ...), ...
```

Classification `library-statement-changed`.  Fix: change the `z3` step to
prove `∃x. x ∈ s ∧ f x < g x` and adjust the surrounding goal; one theorem
re-proof each.

## Group 7 — `sum_eq` lost its `finite s` premise (3)

Theorems:

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `sums.sum_restrict` | `AssertionError: apply_theorem: too many prevs.` | `id=2, rule=apply_theorem, args='sum_eq'` (prevs `0,1`) | high | one line: drop the `finite s` prev and use it in the `intros` step |
| `sums.sum_eq_superset` | same | `id=5, rule=apply_theorem, args='sum_eq'` (prevs `0,2`) | high | one line |
| `sums.sum_multicount_gen` | same | `id=4, rule=apply_theorem, args='sum_eq'` (prevs `0,3`) | high | one line |

**Evidence.**  `47ce6eb1` (2020-05-08) removed the `finite s` premise from
`sum_eq`:

```text
$ git show 47ce6eb1 -- library/iterate.json | sed -n '109,115p'
-                    "th": "⊢ finite s ⟶ (∀x. x ∈ s ⟶ f x = g x) ⟶ sum s f = sum s g"
...
-            "prop": "finite s ⟶ (∀x. x ∈ s ⟶ f x = g x) ⟶ sum s f = sum s g",
+            "prop": "(∀x. x ∈ s ⟶ f x = g x) ⟶ sum s f = sum s g",
```

The three proofs were added in the same commit (or use the new form) but still
pass `finite s` as a previous fact, so `apply_theorem` sees more prevs than
premises.  `sum_restrict` fails at `47ce6eb1` already:

```text
$ cd /tmp/repo47 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_restrict
EXC AssertionError | apply_theorem: too many prevs.
```

Classification `library-statement-changed`.  The fix is a local proof edit,
not a statement change.

## Group 8 — `sub_abs` was renamed to `sum_abs` (1)

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `sums.sum_abs_le` | `TheoryException: Theorem sub_abs not found` | `id=2, rule=apply_theorem_for, args='sub_abs, {f: f, s: s}'` | high | one line: `sub_abs` → `sum_abs` |

**Evidence.**  `sub_abs` existed at `722d4dc6` with the same statement as
today's `sum_abs`, and `47ce6eb1` renamed it without updating this proof:

```text
$ cd /tmp/repo722 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_abs_le
CHECK OK
$ cd /tmp/repo47 && PYTHONPATH=. python /tmp/oldparse.py iterate sum_abs_le
EXC TheoryException | Theorem sub_abs not found
```

The current `sums.json` contains `sum_abs` (same proposition) and no `sub_abs`.
Classification `library-statement-changed`.  Fix is one line in the proof.

## Group 9 — Z3 returns `unknown` for `real_down` (1)

| Theorem | Error | First failing step (id, rule, args) | Confidence | Fix size |
|---|---|---|---|---|
| `real.real_down` | `AssertionError: Z3: not solved.` | `id=1, rule=z3, args='∃e. 0 < e ∧ e < d'` (prevs `0`) | high | environment: need a newer Z3, or a witness proof |

**Evidence.**  Calling the solver directly on the same goal (with the theory
loaded and the variable context set):

```text
$ PYTHONPATH=. python -c "... z3wrapper.solve_core(z3.Solver(), t, debug=True) ..."
A d > 0
C Exists(e, And(e > 0, e < d))
check: unknown
unsat? False
```

The installed solver is the very old `z3-solver 5.3.3.0`, while
`pyproject.toml` asks for `z3-solver>=4.12`:

```text
$ pip show z3-solver | head -3
Name: z3-solver
Version: 5.3.3.0
```

The baseline also fails this theorem after 6.91 s (not the 60 s limit), i.e.
Z3 answers `unknown`, not a timeout.  Classification
`z3-version/timeout`.  Fix: install a recent 4.x Z3 in the test environment, or
replace the `z3` line by an explicit witness (e.g. `d/2`); no library
statement change is needed.

## Found, not fixed

1. **`set.nat_finite` is flaky under `--jobs 2`.**  It is `ok` in
   `docs/library_check.tsv` (96 steps, 0.35 s).  Checking `set` alone gives
   `ok` in 0.29 s, and `set real --jobs 2` also gives `ok` in 0.30 s.  But in
   three runs of
   `PYTHONPATH=. python scripts/check_library.py logic_base set sums real --jobs 2`
   it failed with `AssertionError: Z3: not solved.` after 60.34 s in one run
   and was `ok` (0.30 s) in the next:

   ```text
   run 1 fail 60.34 Z3: not solved.
   run 2 ok 0.30
   ```

   This is Z3 nondeterminism/CPU contention, not a library failure.  It is not
   part of the required failing set (the baseline row is `ok`), but it means
   `--jobs 2` can make a baseline `ok` row look like a regression.  I did not
   change the script or the baseline.
2. **The 9 conclusion-only type-variable failures may be more widespread.**
   I only searched `finite_empty` in `set.json`/`sums.json` for this task; other
   theories that use inductive predicate rules the same way may have the same
   pattern.
3. **The printer bug for `of_nat 0/1` is general**, not specific to the two
   failing theorems: any term of the form `f (of_nat 0)` or `f (of_nat 1)` is
   printed without the parentheses around the argument and cannot be re-parsed.
   I only checked the theorem strings needed for this triage; other theories may
   have stored strings with the same shape.
4. **Test-suite counts differ from `docs/test_baseline.txt`** (77 failed, 653
   passed now versus the 91-line baseline).  This is from work already merged on
   `main` before this branch; this task changed no code, so the suite result is
   unchanged by it.

## Questions for Alex

1. **Conclusion-only type variables (9 theorems).**  Should
   `apply_theorem[_for]` be extended to leave and generalise a type variable
   that appears only in the conclusion, or should each of these nine
   certificates be re-proofed differently?  The current macro generalises only
   term variables, so there is no way to write the certificate in the current
   proof language.
2. **`rewr_conv` ill-typed match (6 theorems).**  Do you prefer a type check in
   `matcher.first_order_match` for bare `SVar` patterns, or a
   `try/except InvalidDerivationException` around `pt.substitution` in
   `rewr_conv`?  Both make all six check; the second is smaller but hides the
   real cause one level deeper.
3. **Eta-expanded statements (`someI`, `some_the`, `nsum_multicount_gen`).**
   Should the library statements be eta-shortened, or should the checker /
   `can_prove` treat eta-equivalent terms as equal?  This is a statement
   change if we fix it in the library, so I did not choose.
4. **Quarantine or re-proof?**  For the four never-checked certificates
   (`trivial`, `member_delete`, `card_insert`, `card_image_inj`), is the
   decision-5 quarantine (replace the proof with `sorry`) the intended route,
   or should they be re-proofed for v0.1.0?
5. **`trivial`.**  Its proof was added in 2020; before that it was an axiom.
   Should we simply drop the proof again (making it an axiom) rather than
   re-prove it without `intros`?
6. **Z3.**  Can the release/test environment pin a recent `z3-solver` (the
   current 5.3.3.0 meets `>=4.12` numerically but is ancient and returns
   `unknown`)?  Or should `real_down` get an explicit witness proof so it does
   not depend on Z3's quantifier handling?
7. **Round-trip regression test.**  Should WS0 get a test that prints and
   reparses every stored `th`/`args` string?  The `f8e0462a` class of failures
   (`real_inv_neg` here, possibly more elsewhere) and the live printer bug for
   `of_nat 0/1` would both have been caught by it.
8. **Printer fix for `of_nat 0/1`.**  Is the right fix to extend the `Number`
   special-case in `pprint.helper` to 0 and 1 (so the priority and the printed
   form agree), or to change `get_priority_pair` to stop treating `of_nat 0/1`
   as an atom?  Either is one line, but the first changes how `of_nat 0/1`
   prints as a whole term.

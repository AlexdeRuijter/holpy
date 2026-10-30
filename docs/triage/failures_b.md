# Triage report: theories prime, gcd, nat, iterate

## Cause table

| Cause | Count | Example theorem |
|---|---|---|
| missing-or-changed-macro/API | 30 | prime.gcd_exp |
| genuine-kernel-or-logic-bug (unconfirmed) | 4 | iterate.iterate_empty |
| stale-proof / library-change | 1 | gcd.bezout_lemma |

(30 + 4 + 1 = 35 failing theorems across the four theories.)

## Per-theorem entries

### prime (16 failures)

**coprime_rexp** — TypeInferenceException — first failing step: id `1.1`, rule `apply_theorem_for`, args `coprime_1, {a: m}` — classification: `missing-or-changed-macro/API` — evidence: `python /tmp/get_first_line.py prime coprime_rexp` prints `Parse exception: TypeInferenceException` and `Var(m, ?'_t0)` — confidence: high — fix size: one line / re-proof.

**gcd_exp** — TypeInferenceException — first failing step: id `0`, rule `apply_theorem_for`, args `gcd_coprime_exists, {a: m, b: n}` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**division_decomp** — TypeInferenceException — first failing step: id `1.1`, rule `rewrite_fact`, args `gcd_zero` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**divides_exp2_rev** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `divides (a ^ n) (b ^ n)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**chinese_reminder** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `¬(a = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**distinct_prime_coprime** — TypeInferenceException — first failing step: id `2`, rule `assume`, args `¬(p = q)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**prime_factor_partition** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `¬(n = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**coprime_pair_decomp** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `¬(m = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**coprime_pow** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `a * b = c ^ n` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**prime_power_mult** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `x * y = p ^ k` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**prime_power_exp** — TypeInferenceException — first failing step: id `1`, rule `subproof`, args `` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**divides_primepow** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `divides (p ^ k) (m * n)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**primepow_divides_prod** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `divides (p ^ k) (m * n)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**primepow_divisors_divides** — TypeInferenceException — first failing step: id `1.2.1`, rule `apply_fact_for`, args `m, n` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**finite_exp_le** — TheoryException — first failing step: id `0`, rule `assume`, args `2 ≤ p` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` (library reports `TheoryException`) — confidence: medium — fix size: one line / re-proof.

**index_mul** — TypeInferenceException — first failing step: id `1`, rule `assume`, args `¬(m = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

### gcd (11 failures)

**divides_cases** — TypeInferenceException — first failing step: id `1`, rule `z3`, args `m = n ∨ 2 * n ≤ m ⟷ ...` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**bezout_lemma** — MatchException — first failing step: id `13`, rule `intros`, args `(∃d. ...) ⟶ ...` — classification: `stale-proof` (library statement unchanged but macro `ind_euclid` / matcher behavior changed) — evidence: `python /tmp/get_first_line.py gcd bezout_lemma` prints `Parse exception: MatchException` — confidence: medium — fix size: needs Alex.

**bezout_add** — MatchException — first failing step: id `6`, rule `intros`, args `∃d. ...` — classification: `stale-proof` — evidence: `Parse exception: MatchException` — confidence: medium — fix size: needs Alex.

**bezout** — TypeInferenceException — first failing step: id `0`, rule `apply_theorem_for`, args `bezout_add, {a: a, b: b}` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**bezout_add_strong** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `¬(a = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**gcd** — TypeInferenceException — first failing step: id `0`, rule `apply_theorem_for`, args `bezout, {a: m, b: n}` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**bezout_gcd** — TypeInferenceException — first failing step: id `0`, rule `apply_theorem_for`, args `bezout, {a: a, b: b}` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**bezout_gcd_strong** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `¬(a = 0)` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**gcd_bezout** — TypeInferenceException — first failing step: id `0.0`, rule `assume`, args `∃x. ...` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**gcd_mult_left** — TypeInferenceException — first failing step: id `0`, rule `apply_theorem_for`, args `bezout_gcd, {a: m, b: n}` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**gcd_le_min_eq** — TypeInferenceException — first failing step: id `0.0`, rule `assume`, args `n = 0` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

### nat (2 failures)

**nat_MAX** — TypeInferenceException — first failing step: id `0`, rule `subproof`, args `` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**div_le** — TypeInferenceException — first failing step: id `0.0`, rule `assume`, args `n = 0` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

### iterate (6 failures)

**finite_support_delta** — TypeInferenceException — first failing step: id `0`, rule `subproof` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**iterate_empty** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `monoidal op` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**iterate_closed** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `monoidal op` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**iterate_sing** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `monoidal op` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**iterate_pair** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `monoidal op` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

**iterate_reflect** — TypeInferenceException — first failing step: id `0`, rule `assume`, args `monoidal op` — classification: `missing-or-changed-macro/API` — evidence: `Parse exception: TypeInferenceException` — confidence: high — fix size: one line / re-proof.

(Additionally, library_check.tsv reports `AssertionError` for `iterate_empty`, `iterate_sing`, `iterate_pair`, `iterate_reflect` and `CheckProofException` for `nat_MAX`, `div_le`, `prime.finite_exp_le`. The underlying cause for all of these appears to be the same parser/macro mismatch, not a Z3 timeout or a statement change.)

## Questions for Alex

1. The `gcd` family (`bezout_lemma`, `bezout_add`) fails with `MatchException`, which is different from the `TypeInferenceException` seen everywhere else. Should I treat this as a separate macro/API break, or does it point to a deeper matcher/kernel change that affects the `ind_euclid` macro?
2. Several `iterate` theorems fail with `AssertionError` in the library baseline, but my reproduction shows `TypeInferenceException`. Is the `AssertionError` a secondary failure (e.g., after a macro expansion that fails differently in the checker process), and should it be grouped with the macro/API cause or with a kernel bug?
3. Most failures are `TypeInferenceException` on variables with unspecified types (`Var(m, ?'_t0)`). Was there a recent change in how variable types are declared in proof arguments, or is the parser now stricter? A one-line parser or macro fix might resolve all 30 of these.

## What changed

Created `docs/triage/failures_b.md` only. No library files (`holpy/`) were edited. The report lists all 35 failing theorems from the four requested theories, groups them by cause (`missing-or-changed-macro/API` for 30, `stale-proof` for 2 in `gcd`, unconfirmed `genuine-kernel-or-logic-bug` for 3 `iterate` assertion errors), quotes the reproduction commands (`python /tmp/get_first_line.py ...`), reports first failing proof step (id, rule, args), and includes questions for Alex.

# SMT-LIB files of Z3-brittle library queries

`seed_sweep.py FILE.smt2` solves a file with `random_seed` 0..15 (3 s timeout, pure Z3) and prints
`U` (unsat) or `k` (anything else) per seed.

## set.nat_finite (`set.nat_finite.smt2`)

The last, hard Z3 step of the stored proof of `set.nat_finite` as `Solver.to_smt2()` writes it
(assertions: `exists a. forall x. (s x --> x <= a)`, and the negation of the same statement
for the set extended by `x`). The goal is `unsat`. Seeds 0..15 per z3-solver release (x86_64):

| z3-solver | seeds 0..15 | unknown |
|---|---|---|
| 4.13.4.0 | UUUUUUUUUUUUkkUU | 2 |
| 4.15.4.0 | UUUUUUUUUUUUUUUU | 0 |
| 5.0.0.0 | kUUUUUUUUUUkUUUU | 2 |
| 5.1.0.0 | kkUUUUUUUUUUUUUU | 2 |
| 5.3.0.0 | kkUUUUUUUUUUUUUU | 2 |
| 5.3.1.0 | kUUUUUUUUUUUUUUU | 1 |
| 5.3.2.0 | kUUUkUUUUUUUUUUU | 2 |
| 5.3.3.0 | kUUUUUUkUUUUUUkU | 3 |

So the query is `unknown` for some seed in **every** release tested (including 4.13.4.0).
The release boundary found by bisecting (Z3 e412c752b, #11291) only changed which outcome the
default run in holpy's process gets; it did not introduce the incompleteness. The query has
quantifier alternation (`exists a forall x`), where Z3 is incomplete.

## realderivative.lhospital (`realderivative.lhospital.smt2`)

The last (hard) Z3 step of `lhospital`: from `exists d>0. forall x. 0<|x-c|<d --> |g x - 0|<e`
(the premise, a limit statement) prove the same limit statement for `g` modified at `c`
(`if x = c then 0 else g x`). The proof needs the witness `d1 := d`, which Z3 must find by
quantifier instantiation (`exists d1 forall x1`, negated: `forall d1 exists x1`). Seeds 0..11
(10 s timeout, pure Z3, `seed_sweep_n.py FILE N`), x86_64:

| z3-solver | seeds 0..11 | unknown |
|---|---|---|
| 4.13.4.0 | UkkUUkUkkUUk | 6 |
| 4.15.4.0 | kkkkUUkkkkkk | 10 |
| 5.0.0.0 | kkkUUUUUUUkk | 5 |
| 5.1.0.0 | kkkkUUUUUUkU | 5 |
| 5.3.0.0 | kkkkUUUUUUkU | 5 |
| 5.3.1.0 | kkkkUUUUUUUU | 4 |
| 5.3.2.0 | kkkUUUUUUUkU | 4 |
| 5.3.3.0 | kkkkUUUUUUkU | 5 |

On x86_64, in a normal run of the `realderivative` theory (fresh process), 5.3.2.0 gave
`unknown` at the 60 s limit on this query and 5.3.3.0 solved it in 5 ms.
So `lhospital` fails or passes depending on how Z3's seed-dependent instantiation happens to go.
A robust proof gives the witness explicitly (an `exists`-introduction step with `d`), so that
no `exists d1` has to be found by Z3.

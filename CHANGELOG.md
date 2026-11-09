# Changelog

All notable changes to holpy are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- PyPI packaging for `holpy` 0.1.0: hatchling build, Python `>=3.10`, core
  dependencies `lark>=1.1`, `sympy>=1.9` and `z3-solver>=4.12`, and a wheel
  configuration that ships `holpy/library/*.json` and excludes the test
  packages.
- GitHub Actions CI (`.github/workflows/ci.yml`) with lint, pytest on Python
  3.10–3.13, Windows/macOS smoke tests, a wheel build/install smoke test, and a
  library job at both ends of the supported Z3 range (PR #24).
- `scripts/compare_test_baseline.py` and `docs/test_baseline.txt`, which fail CI
  when a test that is not a recorded baseline failure fails or errors.
- Theory search path: `holpy.theory_path()`, `holpy.add_theory_path()` and
  `holpy.find_theory()`, exported from `holpy` (PR #15). `HOLPY_THEORY_PATH`
  adds directories searched before the bundled library; `HOLPY_USER_DIR`
  overrides the user data root; `HOLPY_LIBRARY_DIR` still selects a writable
  library checkout. The first file with a theory name wins, shadowing is
  logged once, and adding a path clears the loader caches.
- `holpy.proofs` with `Level`, `ProofContext`, `expand`, `condense`,
  `level_of`, `oracles`, `expand_theory` and `condense_theory`, implemented for
  the `MACRO` and `ANNOTATED` levels (PR #28). `MACRO` drops `th` where checking
  does not need it; `ANNOTATED` fills in missing `th`; the `*_theory` functions
  set a top-level `proof_level` hint and support `steps="keep"|"drop"`.
- A canonical theory JSON writer, `holpy.proofs.dumps_theory` and
  `write_theory`: sorted keys, stable separators, one content/proof/steps entry
  per line, UTF-8 with `ensure_ascii=False`, exactly one trailing newline (PR
  #27).
- The macro contract test (`holpy/macros/tests/macros_contract_test.py`): it
  checks that every non-oracle macro expands, every oracle has level 0, argument
  signatures round-trip through printer/parser, and the macro expansion graph is
  acyclic (PR #48).
- `scripts/check_library.py` and its checked-in baseline
  `docs/library_check.tsv`: replay every stored certificate in a fresh process
  per theory, report `ok`/`fail`/`gaps`/`noproof`, bound each Z3 call
  (`--z3-timeout`, default 60 s), compare TSVs, and allow the Z3-brittle
  theorems in `scripts/z3_brittle.txt`. The baseline has 3,763 theorem rows.
- `docs/triage/z3_smtlib/` (SMT-LIB queries, a witness variant and seed-sweep
  scripts), `docs/triage/z3_library_queries/` (whole-library query records for
  z3-solver 5.3.2.0 and 5.3.3.0), `docs/triage/z3_proof_seed_matrix.md` and its
  script, and `docs/z3.md`.
- New expandable macros from PR #2: `induct`, `real_linarith`, `nat_linarith`,
  `exI_list`, `conj_intro`, `conj_elim`, `contr`, `cases`, `semiring_norm` and
  `transfer`.
- `holpy.data.real` no longer loads `interval_arith` at import time; the theory
  is loaded lazily (PR #14, PR #51).

### Fixed

- Kernel issue #3: `Term.occurs_var` treats a schematic variable as occurring
  in itself, so `forall_intr` and `abstraction` cannot quantify over a schematic
  variable that is free in the hypotheses (PR #54). The reproduction is covered
  by `holpy/kernel/tests/soundness_test.py`.
- Kernel issue #5: `Theory.checked_extend` now compares the theorem proved by
  the supplied proof with the stated theorem, rejects a mismatch, and does not
  register it (PR #55). A correct proof with fewer hypotheses is still accepted.
- Matcher: `rewr_conv` rejects ill-typed bare-variable matches instead of
  attempting an invalid substitution (PR #37), and `implies`/`all` matching no
  longer raises `MatchException` in the prime and gcd proofs (PR #40).
- `intros` handles nested existentials by moving the inner binders into the
  antecedent with `exE` (PR #40).
- `apply_theorem`/`apply_theorem_for` proof arguments now print and parse their
  type instantiation, and 16 stored library proof lines were restored to the
  round-tripping form (PR #45). This also makes the conclusion-only type
  variable proofs in `card`, `iterate`, `products`, `set` and `sums` check.
- `Monomial.__le__` returns a real `bool`, so equality and sorting of
  coefficients work (PR #25).
- Imperative `ArrayElt.convert_hol` and `Field.convert_hol` now convert their
  subexpressions through the methods; `holpy/imperative/tests/convert_hol_test.py`
  covers both (PR #60).
- Z3 5.x compatibility: proof generation is no longer enabled globally with
  `z3.set_param(proof=True)`; `solve_and_proof` uses a private
  `z3.Context(proof=True)`, and `z3wrapper.solve` no longer generates proofs.
  `Suc x` is translated to `x + 1`. The `z3-solver` upper bound was removed and
  CI checks 5.3.2.0 and the newest release; library checking bounds each Z3
  call. See `docs/z3.md`.

### Changed

- The distribution is now the single `holpy.*` package. The web IDE, SMT
  reconstruction, SAT and `holsmt` code are on the `archive/webapp` and
  `archive/smt` branches and are no longer importable from `main`; the Flask
  dependencies were removed.
- `holpy.integral` is explicitly experimental in 0.1.0 (see `README.md`).
- Theory lookup is path-based: `basic.load_metadata` scans the theory search
  path, `basic.user_file` returns the first matching file (or today's default
  path when the name is not found), and a rewrite writes back to the file that
  was read. A theory that is shadowed by an earlier directory logs one warning.
- A proof line without a `th` key now means "no stated theorem" rather than
  raising `KeyError` (`holpy/syntax/parser.py`).
- Code that relied on `z3wrapper` setting `proof=True` globally must now use
  `solve_and_proof`, whose proof and assertions belong to a private Z3 context.
- **Not changed:** `simplex_macro`, `integer_simplex` and `real_eq_comparison`
  remain trusted level-0 oracles in this branch (`holpy/proofs/levels.py`). The
  commit that makes them expand, `29ffad89`, is not an ancestor of this branch.

### Known issues

- The recorded library baseline (`docs/library_check.tsv`) has 1,988 `ok`, 1,587
  `noproof`, 81 `gaps` and 107 `fail` rows out of 3,763 theorems;
  `docs/triage/failures_d.md` re-checked `main` at `cca073b4` and found 68
  failures (66 deterministic plus the two Z3-brittle ones), and 52 after the
  TyInst fix that is merged here. The largest causes are missing parentheses
  around numeric `of_nat 0/1` and `-0` in the printer (15), conclusion-only type
  variables (15, fixed by PR #45), ambiguous `of_nat` under unary negation (5),
  parser `variable` scoping (3) and eta-expanded stored statements (3); the rest
  are stale certificates, local certificate defects, the `nat_const_ineq`
  macro, and the two Z3-brittle theorems below.
- `holpy.integral` is experimental in 0.1.0: 58 tests are marked
  `@unittest.expectedFailure`, and `expr_test.py` does not collect on its own
  because of global theory state.
- Open geometry issues #17 and #18 (`holpy/geometry/expr.py`): `Circle.__eq__`
  reads `other.center` before its `isinstance` check and raises `AttributeError`
  for a non-`Circle`, and `Fact.__init__` accepts but ignores `tail` (always
  sets `self.tail = False`).
- `holpy/prover/tests/proofrec_test.py::ProofrecTest::testRecSolveSet` still
  fails with `NotImplementedError`; it is the only entry in
  `docs/test_baseline.txt`.
- `const_inequality` is an unverified floating-point oracle with no error
  bound: it compares values from `eval_hol_expr`, which falls back to
  `real_approx_eval` (Python `int`/`float` arithmetic) when exact evaluation
  fails, and is registered at level 0 (no expansion).
- Z3-brittle theorems: `set.nat_finite` and `realderivative.lhospital` can
  change status with the Z3 version, platform or process; they are listed in
  `scripts/z3_brittle.txt`.
- Kernel issues #4 (`Term.subst` accepts open or ill-typed values) and #6 (the
  checker does not validate constants) are not fixed in this release; their
  reproductions are `@unittest.expectedFailure` tests in
  `holpy/kernel/tests/soundness_test.py`.
- `Level.PRIMITIVE` is defined, but `expand` and `condense` raise
  `NotImplementedError` for it; only `MACRO` and `ANNOTATED` are implemented.

# Changelog

All notable changes to holpy are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

First alpha release. The public API may change before 1.0.

### Added

- PyPI packaging for `holpy` 0.1.0: hatchling build, Python `>=3.10`, core
  dependencies `lark>=1.1`, `sympy>=1.9` and `z3-solver>=4.12`, and a wheel that
  ships `holpy/library/*.json` and excludes the test packages.
- GitHub Actions CI (`.github/workflows/ci.yml`) with lint, pytest on Python
  3.10–3.13, separate Windows and macOS jobs, a wheel build/install smoke test,
  and a library job at both ends of the supported Z3 range (PR #24).
  `scripts/compare_test_baseline.py` and `docs/test_baseline.txt` fail CI when a
  test that is not a recorded baseline failure fails or errors.
- Theory search path: `holpy.theory_path()`, `holpy.add_theory_path()` and
  `holpy.find_theory()`, exported from `holpy` (PR #15). `HOLPY_THEORY_PATH`
  adds directories searched before the bundled library; `HOLPY_USER_DIR`
  overrides the user data root; `HOLPY_LIBRARY_DIR` still selects a writable
  library checkout. The first file with a theory name wins, shadowing is
  logged once, and adding a path clears the loader caches.
- `holpy.proofs` with `Level`, `ProofContext`, `expand`, `condense`,
  `level_of`, `oracles`, `expand_theory` and `condense_theory` (PR #28).
  `MACRO` drops `th` where checking does not need it; `ANNOTATED` fills in
  missing `th`; `PRIMITIVE` replaces every non-oracle macro line by a
  `subproof` line holding its expansion, keeping the original rule, arguments
  and `prevs` in `expanded_from` (`expand`), copies the proof at `condense`,
  and is returned by `level_of` when no expandable macro line remains and every
  line has a statement. The `*_theory` functions set `proof_level` and support
  `steps="keep"|"drop"`.
- A canonical theory JSON writer, `holpy.proofs.dumps_theory` and
  `write_theory` (PR #27), and the macro contract test in
  `holpy/macros/tests/macros_contract_test.py`: every non-oracle macro expands,
  every oracle has level 0, argument signatures round-trip, and the expansion
  graph is acyclic (PR #48).
- `scripts/check_library.py` and its checked-in baseline
  `docs/library_check.tsv`: replay every stored certificate in a fresh process
  per theory, report `ok`/`fail`/`gaps`/`noproof`, bound each Z3 call
  (`--z3-timeout`, default 60 s), compare TSVs, and allow the Z3-brittle
  theorems in `scripts/z3_brittle.txt` (PR #62 parses each proof once and
  defaults `--jobs` to one less than the CPU count). `scripts/bench_kernel.py`
  times the kernel checking phase on its own (PR #61). The compiled lark
  grammars are cached in `holpy._paths.cache_dir()`, which follows
  `HOLPY_USER_DIR` (PR #65).
- Z3 triage material under `docs/triage/` and `docs/z3.md`.
- New expandable macros from PR #2: `induct`, `real_linarith`, `nat_linarith`,
  `exI_list`, `conj_intro`, `conj_elim`, `contr`, `cases`, `semiring_norm`,
  `transfer`. `holpy.data.real` loads `interval_arith` lazily (PR #14, #51).

### Fixed

- Kernel issue #3 (PR #54): `Term.occurs_var` treats a schematic variable as
  occurring in itself, so `forall_intr` and `abstraction` cannot quantify over
  a schematic variable that is free in the hypotheses. Kernel issue #5 (PR
  #55): `Theory.checked_extend` rejects and does not register a proof whose
  result does not prove the stated theorem.
- Kernel issue #4 (PR #56): the `substitution` primitive rule rejects an open
  or ill-typed value with `InvalidDerivationException`, which `check_proof`
  raises as `CheckProofException`; the reproduction in
  `holpy/kernel/tests/soundness_test.py` now raises instead of deriving an
  unsound equality. `Term.subst` itself still substitutes its values unchecked,
  as its docstring says, for non-kernel callers that do not need those
  guarantees.
- Kernel issue #6 (PR #59): `check_proof` validates the constants and types of
  primitive-rule arguments against the theory, and a final-theorem guard
  validates the final statement's constants, so the Issue #6 reproduction in
  `holpy/kernel/tests/soundness_test.py` raises `CheckProofException`. Statements
  taken from `theorem` lines and from macro evaluation are still trusted and
  are not re-checked.
- Checker exception hygiene (PR #74): a bad primitive-rule call raises
  `CheckProofException` instead of `AttributeError`, and an ill-typed
  `forall_elim` argument is reported as `InvalidDerivationException`; a
  `TypeError` raised inside a rule is no longer swallowed.
- `rewr_conv` rejects ill-typed bare-variable matches instead of attempting an
  invalid substitution (PR #37), `implies`/`all` matching no longer raises
  `MatchException` in the prime and gcd proofs, and `intros` moves the binders
  of nested existentials into the antecedent with `exE` (PR #40).
- `apply_theorem`/`apply_theorem_for` proof arguments now print and parse their
  type instantiation, and 16 stored library proof lines were restored to the
  round-tripping form (PR #45). This also makes the conclusion-only type
  variable proofs in `card`, `iterate`, `products`, `set` and `sums` check.
- The printer parenthesises `of_nat 0`, `of_nat 1` and negative zero, so the
  affected library statements print back to the stored text (PR #71), and
  `parse_proof` scopes a subproof's variable declarations to that subproof (PR
  #70).
- `Monomial.__le__` returns a real `bool` (PR #25), and imperative
  `ArrayElt.convert_hol` and `Field.convert_hol` convert their subexpressions
  through the methods (PR #60).
- Z3 5.x compatibility: proof generation is no longer enabled globally with
  `z3.set_param(proof=True)`; `solve_and_proof` uses a private
  `z3.Context(proof=True)`, and `z3wrapper.solve` no longer generates proofs.
  `Suc x` is translated to `x + 1`. The `z3-solver` upper bound was removed and
  CI checks 5.3.2.0 and the newest release (see `docs/z3.md`). Code that relied
  on the global setting must use `solve_and_proof`.

### Changed

- The distribution is now the single `holpy.*` package. The web IDE, SMT
  reconstruction, SAT and `holsmt` code and their Flask dependencies are no
  longer part of the tree and are not importable.
- `holpy.integral` is explicitly experimental in 0.1.0 (see `README.md`).
- `simplex_macro`, `integer_simplex` and `real_eq_comparison` now expand and
  have level `None` instead of being trusted level-0 oracles (PR #74).
- Theory lookup is path-based: `basic.load_metadata` scans the theory search
  path, `basic.user_file` returns the first matching file (or today's default
  path when the name is not found), and a rewrite writes back to the file that
  was read. A theory that is shadowed by an earlier directory logs one warning.
- A proof line without a `th` key now means "no stated theorem" rather than
  raising `KeyError` (`holpy/syntax/parser.py`).
- CI splits the Windows and macOS jobs and skips the macOS job while GitHub
  reports an Actions or macOS incident; superseded runs are cancelled (PR #72).

### Known issues

- Library replay (`scripts/check_library.py --jobs 1`, all 3,763 theorem rows)
  on `main` at `880edb89` gives `ok` 2047, `gaps` 81, `noproof` 1587 and `fail`
  48. `ok` means the stored proof replays in this kernel, not that the library
  is verified: 1,587 of the 3,763 theorems have no stored proof at all and are
  therefore not verified, 48 fail to replay, and `gaps` rows check but contain
  `sorry`. The checked-in `docs/library_check.tsv` (ok 1988, fail 107)
  predates several fixes.
- The test suite on `main` at `880edb89` with Python 3.14.4 gives 1 failed,
  790 passed, 1 skipped and 59 xfailed. The failure is
  `proofrec_test.py::ProofrecTest::testRecSolveSet` (`NotImplementedError`),
  the only entry in `docs/test_baseline.txt`; `compare_test_baseline.py` exits 0.
- Z3 answers are not deterministic for a few theorems: `set.nat_finite` and
  `realderivative.lhospital` can change status with the Z3 version, platform or
  process, and are listed in `scripts/z3_brittle.txt` (see `docs/z3.md`).
- **Trusted components.** Z3 and `holpy.integral` use numerical or trusted
  components. Eleven level-0 macros are oracles, not expanded to kernel
  inferences (`holpy.proofs.levels.ORACLES`): `const_inequality`,
  `int_const_ineq`, `int_eval`, `nat_eval`, `real_compare`, `real_const_eq`,
  `real_const_ineq`, `real_eval`, `real_norm`, `sympy` and `z3`.
  `const_inequality` in particular is an unverified floating-point oracle with
  no error bound: it compares values from `eval_hol_expr`, which falls back to
  `real_approx_eval` (`int`/`float` arithmetic) when exact evaluation fails.
  `holpy.integral` decides inequalities through those numerical paths and calls
  `sympy` directly.
- `holpy.integral` is experimental in 0.1.0: its tests mark 58 tests
  `@unittest.expectedFailure`, and its API may change.
- `Level.PRIMITIVE` needs each stored proof to print back; `nat_MAX` and
  `div_le` fail before expansion because a stored line cites itself.
- Open geometry issues #17 and #18 (`holpy/geometry/expr.py`): `Circle.__eq__`
  reads `other.center` before its `isinstance` check, and `Fact.__init__`
  ignores `tail` (always `False`).

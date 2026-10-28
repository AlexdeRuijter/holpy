# WS0: library check tool and baseline

**Wave 0. One agent, about half a day. Every other workstream's acceptance
checks depend on this.**

## Brief

Build a script that checks every *stored proof* in the bundled library and
records the result per theorem, then commit the result as the baseline.

Why a new tool: `holpy.server.monitor.check_theory` replays `steps` (the tactic
script) when a theorem has them, and only checks the stored `proof` otherwise.
The stored `proof` is the certificate, and it is what WS1 condenses, so that is
what must be checked.

## Task WS0-1: `scripts/check_library.py`

**Behaviour.**

```
python scripts/check_library.py [THEORY ...] [--out FILE] [--jobs N] [--check-level 0]
```

- With no theory names, checks every theory in `holpy._paths.library_dir()` in
  import order (`basic.get_import_order`).
- For each theorem item with a `proof`: parse it with `server.parse_proof` in
  the item's variable context, run `check_proof(no_gaps=False)` and record
  `theory`, `name`, `status` (`ok`, `gaps` (contains `sorry`), `fail`),
  `error type` (for `fail`), `statement` as printed, kernel `steps` from the
  `ProofReport`, `macros_eval` (sorted, comma-separated) and wall-clock seconds.
  Theorems with no `proof` get status `noproof`.
- Writes a TSV (default `docs/library_check.tsv`), sorted by theory then item
  order, with times rounded to 0.01 s. Everything except the time column must
  be deterministic, so two runs give the same file apart from times.
- `--jobs N` checks theories in parallel processes. A theory's dependencies are
  loaded in each process; results are identical to `--jobs 1`.
- Uses `logging`, exits 0 even when theorems fail (the TSV is the result).
- A `--compare OLD.tsv` option prints the theorems whose `status`, `statement`
  or `steps` differ, and the total time before and after, and exits 1 if any
  theorem went from `ok` to anything else.

Reuse [prototypes/slim_check.py](prototypes/slim_check.py) for the loading
pattern. It is a throwaway script and has the right calls.

**Tests** (`scripts/tests/check_library_test.py`, `unittest`):

- checking `logic` gives 45 `ok` rows and no `fail`;
- a temporary copy of `logic.json` with one `th` corrupted gives exactly that
  theorem as `fail` (point `HOLPY_LIBRARY_DIR` at a temp directory);
- `--compare` of a file with itself exits 0; with a row changed from `ok` to
  `fail`, it exits 1 and names the theorem.

**Deliverable.** PR with the script, its tests, and the committed baseline
`docs/library_check.tsv` for the whole library on `main`. Report the
per-theory totals and total time in the PR body.

**Acceptance checks.**

```bash
python scripts/check_library.py logic nat --out /tmp/a.tsv && \
python scripts/check_library.py logic nat --out /tmp/b.tsv && \
python scripts/check_library.py --compare /tmp/a.tsv /tmp/b.tsv     # exit 0, no differences
python -m unittest scripts.tests.check_library_test                  # OK
awk -F'\t' 'NR>1{print $3}' docs/library_check.tsv | sort | uniq -c  # status counts, in the PR body
```

## Task WS0-2: test baseline

Commit `docs/test_baseline.txt`: the sorted list of failing and erroring test
IDs from

```bash
pytest holpy -q -p no:cacheprovider --continue-on-collection-errors -rfE
```

on `main`, one per line, with the error type. WS5 works this list down, and
every other PR shows that it adds no line to it.

**Acceptance check.** The file has 91 lines on `main` at cf4f524 (71 failures, 20
errors), or the PR explains the difference.

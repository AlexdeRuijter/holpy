# Documentation

Tutorials and long-form documentation for holpy.

- [Z3 in holpy](z3.md): how holpy calls Z3, why proof generation is not global, supported versions.

## Checking the library

`scripts/check_library.py` replays every stored proof and writes a TSV of the
results, or compares a new TSV with a baseline. Run it from the repository
root:

```bash
python scripts/check_library.py [THEORY ...] [--out FILE] [--jobs N]
python scripts/check_library.py --compare OLD.tsv NEW.tsv
```

`--jobs` defaults to `max(1, os.cpu_count() - 1)`, so a full check uses the
available cores. Each theory is checked in a fresh worker process, and the
output is ordered by the requested theory order and JSON item order, not by
process order. Use `--jobs 1` for the old single-process order when comparing
timings.

A Z3 answer must not depend on process order: checking the same theory alone,
after another theory, or with a different job count must give the same status,
statement and steps. When it does not, that is a fragility bug in the proof or
the Z3 wrapper, not an allowed difference between runs. See
[Z3 in holpy](z3.md) for why Z3 calls are isolated and which library proofs are
known to be brittle.
## Benchmarking the kernel

`scripts/bench_kernel.py` measures the kernel proof-checking phase separately from theory loading and proof parsing. From the repository root, run `PYTHONPATH=. python scripts/bench_kernel.py [THEORY ...] [--repeat N] [--json FILE]`; the default theories are `nat sums logic`, the default repetition count is 3, and `--json` writes the same per-theory and total user CPU seconds as the printed table. The script also prints the Python version, Z3 version, and holpy git commit it ran on.

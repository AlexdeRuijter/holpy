# Documentation

Tutorials and long-form documentation for holpy.

- [Z3 in holpy](z3.md): how holpy calls Z3, why proof generation is not global, supported versions.

## Benchmarking the kernel

`scripts/bench_kernel.py` measures the kernel proof-checking phase separately from theory loading and proof parsing. From the repository root, run `PYTHONPATH=. python scripts/bench_kernel.py [THEORY ...] [--repeat N] [--json FILE]`; the default theories are `nat sums logic`, the default repetition count is 3, and `--json` writes the same per-theory and total user CPU seconds as the printed table. The script also prints the Python version, Z3 version, and holpy git commit it ran on.

# AGENT-INSTRUCTION

Project-specific rules for working on **holpy**. Read this before changing code.

## Package shape

- Published distribution: `holpy` on PyPI.
- All core code lives under the single `holpy.*` namespace. Never add a new
  top-level importable package. Internal imports are absolute:
  `from holpy.kernel.term import Term`.
- `holpy/library` is package data, addressed through
  `holpy._paths.library_dir()` (or `importlib.resources`). Do not use
  cwd-relative paths such as `library/...`.
- User theories go to `holpy._paths.user_dir(username)`, never inside
  `site-packages`. `HOLPY_USER_DIR` overrides the data root;
  `HOLPY_LIBRARY_DIR` points at a writable checkout for rewriting bundled
  theories.
- `archive/smt` and `archive/webapp` are archives. Do not reintroduce
  `app/`, `smt/`, `sat/`, or `holsmt/` into `main`.

## Python style

The house policy is the qwen workspace's `ruff.toml`:

- Defect families only: `E4`, `E9`, `F`, `W605`; line length 100.
- Style rewrites and formatter churn are not part of ordinary changes.
- New and refactored code uses `from __future__ import annotations`,
  rigorous type annotations, NumPy-style docstrings
  (`Parameters` / `Returns` / `Raises`), and `logging` at explicit levels
  instead of `print`.
- Comments explain **why**, not what the syntax already says.
- Proof scripts and library JSON are certificates. Do not rewrite them
  for style.

## Change scope

- Keep changes focused and reviewable; use one logical change per commit.
- Keep packaging, style, and metadata changes in separate commits.
- Large refactors should be split into reviewable units, for example one
  module per change.
- Do not mix unrelated modules in one change unless the dependency requires it.

## User-specific requirements

If the user gives requirements that are specific to their environment, account,
or workflow and do not generalize to other contributors, create a local,
untracked `LOCAL-AGENT-INSTRUCTION.md` and add it to the local ignore rules.
Keep the upstream repository free of environment-specific instructions,
credentials, tool configuration, and commit/authorship conventions; do not
commit that file or fold its contents into this document.

## Kernel discipline

`holpy/kernel` is the trusted core. Every edit must be behavior-preserving.
For a kernel change:

1. Read the whole affected symbol and its callers before editing.
2. Prefer docstrings, annotations, and comments; do not change logic.
3. Run the kernel tests and the full core suite.
4. Report every kernel change by file and symbol in the change description.
5. If a behavior change is unavoidable, stop and ask.

## Verification

```bash
python -m unittest discover -s holpy/kernel -t . -p "*_test.py"
python -m unittest discover -s holpy -t . -p "*_test.py"   # full suite
python -m build --no-isolation --wheel --outdir dist
```

Also install the wheel in a clean venv and smoke-test:

```python
from holpy.logic import basic
basic.load_theory("logic")
from holpy.data import real
```

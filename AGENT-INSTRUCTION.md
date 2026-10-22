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

## Style-modernization branch/PR policy

Full modernization is split per module, one branch and one PR per module:

- `style/kernel`
- `style/logic`
- `style/data`
- `style/syntax`
- `style/server`
- `style/prover`
- `style/util`
- `style/integral`
- `style/geometry`
- `style/paraverifier`
- `style/imperative`
- `style/macros`

`kernel` and `logic` receive the most thorough documentation and typing.
Do not mix modules in one PR unless the user explicitly asks.

## Kernel discipline

`holpy/kernel` is the trusted core. Every edit must be behavior-preserving.
For a kernel change:

1. Read the whole affected symbol and its callers before editing.
2. Prefer docstrings, annotations, and comments; do not change logic.
3. Run the kernel tests and the full core suite.
4. Report every kernel change by file and symbol in the PR description.
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

## Git and authorship

- Commits must be GPG-signed. Do not use `--no-gpg-sign`.
- Commit identity stays `Alex de Ruijter <noreply.alderuijter@gmail.com>`.
- Copyright/contact metadata uses `A.L.deRuijter@tudelft.nl`.
- Original author is Bohua Zhan `<bzhan@ios.ac.cn>`; keep his credit in
  `pyproject.toml`, `LICENSE`, `AUTHORS.md`, and `README.md`.
- Keep one logical change per commit; do not mix packaging, style, and
  metadata in one commit.

## pi-lens

- Project config is `.pi-lens.json`; formatting and autofix are disabled for
  this repo on purpose.
- `ruff.toml` is the single lint policy source; do not add `[tool.ruff]`
  back to `pyproject.toml`.
- pi-lens 4.4.4+ is required for the corrected `no-assert-tuple` rule.

# holpy

Higher-order logic (HOL) theorem prover and proof assistant in Python.

This distribution contains the core library: kernel, logic, data types, parser,
proof state, automation, and the bundled theory library. The web IDE and the
veriT/SMT proof-reconstruction module are preserved on the `archive/webapp` and
`archive/smt` branches and are not part of the published package.

## Installation

```bash
pip install holpy
```

Requires Python 3.10 or newer. The package bundles its theory library, so no
extra data download is needed. `z3-solver` is a core dependency.

## Quick start

```python
from holpy.logic import basic

basic.load_theory("logic")
print("logic theory loaded")
```

The bundled theories live in `holpy/library`. User-created theories are written
to the platform data directory (for example `~/.local/share/holpy` on Linux),
or to `$HOLPY_USER_DIR` when that variable is set. Set `$HOLPY_LIBRARY_DIR` to
a writable checkout if you need to rewrite the bundled theories.

## Development

```bash
git clone https://github.com/AlexdeRuijter/holpy.git
cd holpy
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The tests can also be run with the standard library:

```bash
python -m unittest discover -s holpy -t . -p "*_test.py"
```

## Layout

* `holpy/kernel`: kernel for higher-order logic (types, terms, theorems, proofs,
  macros, theories, extensions).
* `holpy/logic`: base logic, matching, conversions, tactics, and automation.
* `holpy/data`: standard data types (nat, int, list, set, real, ...).
* `holpy/syntax`: parsing, type inference, and printing.
* `holpy/server`: proof states, tactics, and methods.
* `holpy/prover`: proof reconstruction, SMT/SAT bridges, simplex, omega.
* `holpy/integral`: symbolic integration.
* `holpy/geometry`, `holpy/paraverifier`, `holpy/imperative`: additional
  application modules.
* `holpy/library`: bundled JSON theory library.
* `docs/`: tutorials and long-form documentation.
* `scripts/`: development-only utilities.

## Authors

holpy was created by **Bohua Zhan** (`bzhan@ios.ac.cn`). The kernel, logic,
data types, syntax, proof state, automation, and the original application
modules are his work; the bundled theory library originates from his project.

This distribution is maintained by **Alex de Ruijter**
(`noreply.alderuijter@gmail.com`), who prepared the PyPI packaging, the
`holpy.*` namespace migration, and the build/test infrastructure. See
[`AUTHORS.md`](AUTHORS.md) for the full attribution and contributor list.

## Documentation

* `docs/tutorial/`: notebooks introducing the backend and logic.
* `docs/integral_tutorial/`: symbolic-integration tutorial.
* `holpy/integral/README.md`: integration coverage and references.

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

holpy 0.1.0 is an alpha release. It supports Python 3.10 to 3.13. The package
bundles its theory library, so no extra data download is needed. `z3-solver` is
a core dependency.

## Quick start

Load the bundled `logic` theory and re-check one of its stored proofs:

```python
from holpy.logic import basic, context
from holpy.server import server

basic.load_theory("logic")

data = basic.load_json_data("logic")
item = next(i for i in data["content"] if i["name"] == "conj_comm")
context.set_context(None, vars=item["vars"])
state = server.parse_proof(item["proof"])
print(state.prf.items[-1].th)
```

Output:

```text
|- A & B <--> B & A
```

The bundled theories live in `holpy/library`; the next section explains where
holpy looks for yours.

## Your own theories

holpy searches for `<name>.json` theory files in this order:

1. for a user other than `master`, that user's directory,
   `holpy._paths.user_dir(username)`;
2. the directories in `HOLPY_THEORY_PATH`, split on `os.pathsep`, in order;
3. directories added with `holpy.add_theory_path()`, most recently added first
   unless `prepend=False`;
4. the bundled library, `holpy._paths.library_dir()`.

The first file with a given theory name wins, so an earlier directory shadows
the same name later on the path. Missing directories are skipped with a
warning, and a shadowed name is reported once.

Put your theory in a directory and add that directory at run time:

```python
import holpy
from holpy.logic import basic

holpy.add_theory_path("~/my-theories")   # searched before the bundled library
basic.load_theory("mythy")               # reads ~/my-theories/mythy.json
```

The same directory can be supplied from the environment:

```bash
HOLPY_THEORY_PATH=$HOME/my-theories python your_script.py
```

`HOLPY_USER_DIR` sets the data root for per-user theory directories
(`holpy._paths.user_dir(username)` for a username other than `master`; the
default `master` uses the bundled library). `HOLPY_LIBRARY_DIR` points
`holpy._paths.library_dir()` at another directory, for example a writable
checkout when you need to rewrite the bundled theories; it replaces the
bundled library location, so the built-in theories are found only if that
directory contains them or another search-path entry provides them.

`holpy.find_theory(name)` returns the file that would be loaded and raises
`FileNotFoundError` when the name is not on the path. A theory that needs extra
macros must import their Python module first.

## Proof levels

`holpy.proofs` stores and converts proofs at a chosen amount of detail.
`Level.MACRO` keeps macro-level lines and stores `th` only where checking
requires it; `Level.ANNOTATED` keeps `th` on every line. A stored proof can be
condensed, expanded, or queried:

```python
from holpy.logic import basic
from holpy.kernel import theory
from holpy.proofs import (
    Level, ProofContext, condense, condense_theory, expand, expand_theory,
    level_of,
)

basic.load_theory("logic", limit=("thm", "conj_comm"))
data = basic.load_json_data("logic")
item = next(i for i in data["content"] if i["name"] == "conj_comm")
ctx = ProofContext(vars=item["vars"], thy=theory.thy)

print(level_of(item["proof"], ctx=ctx).name)          # ANNOTATED
compact = condense(item["proof"], Level.MACRO, ctx=ctx)
print(level_of(compact, ctx=ctx).name)                # MACRO
print(expand(compact, Level.ANNOTATED, ctx=ctx)[-1]["th"])
# ⊢ A ∧ B ⟷ B ∧ A
```

`expand_theory(data, level)` and `condense_theory(data, level)` apply the same
operations to every theorem in a theory dictionary; `condense_theory` leaves a
theorem at `ANNOTATED` when condensing would change checking and records its
name on the result's `guard` attribute. `Level.PRIMITIVE` is planned but not
implemented on this branch: passing it raises `NotImplementedError`.

## Checking the library

`scripts/check_library.py` replays the stored proof of each theorem and reports
a per-theorem status (`ok`, `gaps`, `fail`, or `noproof`):

```bash
python scripts/check_library.py logic --out /tmp/logic_check.tsv
```

Not every bundled theorem currently checks: some are known to fail. A recorded
run is in `docs/library_check.tsv`; the known issues will also be listed in
`CHANGELOG.md` once it exists.

## Experimental

`holpy.integral` (symbolic integration) is experimental in 0.1.0. Some of its
tests are marked as expected failures, and its API may change.

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
* `holpy/integral`: symbolic integration (experimental; see above).
* `holpy/geometry`, `holpy/paraverifier`, `holpy/imperative`: additional
  application modules.
* `holpy/library`: bundled JSON theory library.
* `docs/`: tutorials and long-form documentation.
* `scripts/`: development-only utilities.

## Authors

holpy was created by **Bohua Zhan** (`bzhan@ios.ac.cn`). The kernel, logic,
data types, syntax, proof state, automation, and the original application
modules are his work; the bundled theory library originates from his project.

This repository is a fork of Bohua Zhan's holpy, used with his agreement; see
[`AUTHORS.md`](AUTHORS.md) and [`LICENSE`](LICENSE).

This distribution is maintained by **Alex de Ruijter**
(`A.L.deRuijter@tudelft.nl`), who prepared the PyPI packaging, the
`holpy.*` namespace migration, and the build/test infrastructure. See
[`AUTHORS.md`](AUTHORS.md) for the full attribution and contributor list.

## Documentation

* `docs/tutorial/`: notebooks introducing the backend and logic.
* `docs/integral_tutorial/`: symbolic-integration tutorial.
* `holpy/integral/README.md`: integration coverage and references.

# WS2: theory search path

**Wave 1. One agent (A and B can be two). About 1–2 days.**

## Brief

Today holpy finds theories in exactly one directory: `holpy._paths.user_dir(username)`,
which for the default user `master` is the bundled library (or
`$HOLPY_LIBRARY_DIR`). A project that keeps its theories elsewhere must point
`HOLPY_LIBRARY_DIR` at its own folder, and then the bundled `logic`, `nat`,
`real`, `set` … disappear. For holpy to work as an installed library, a user
must be able to add directories that are searched *before* the bundled library.

## Background

- `holpy/_paths.py`: `library_dir()`, `user_data_dir()`, `user_dir(username)`,
  `user_file(filename, username)`.
- `holpy/logic/basic.py`: `load_metadata(username)` lists the `.json` files in
  `user_dir(username)` and caches `imports`/`description` per theory name in
  `theory_cache[username]`. `load_theory_cache`, `query_item_index` and
  `load_json_data` find files through `user_file(filename, username)`, and
  compare modification times to decide when to reload.
- `load_theory_cache` imports Python modules for some theories before loading
  them (`logic` → `holpy.prover.z3wrapper`, `real` → `holpy.data.real`, …), so
  that their macros are registered.
- `holpy/data/real.py` line 30 runs `basic.load_theory('interval_arith')` at
  import time. Since `load_theory_cache('real')` imports `holpy.data.real`,
  loading `real` re-enters the loader. Downstream verifiers work around it.

## Design

### Search order

For username `master`:

1. each directory in `$HOLPY_THEORY_PATH`, split on `os.pathsep`, in order
   (empty entries ignored, `~` expanded, relative paths resolved against the
   current directory once, when first read);
2. each directory added with `holpy.add_theory_path()`, most recently added first
   unless `prepend=False`;
3. the bundled library: `library_dir()` (which still honours `$HOLPY_LIBRARY_DIR`).

For another username, `user_dir(username)` comes first, then the list above.

**The first file with a given theory name wins.** When a name on the path
shadows a name later on the path, log one `WARNING` per name per process,
naming both files. A directory that does not exist is skipped with a
`WARNING` (once).

### Public API (additive)

In `holpy/_paths.py`, re-exported from `holpy/__init__.py`:

```python
def theory_path(username: str = "master") -> list[Path]: ...
def add_theory_path(path: str | os.PathLike, *, prepend: bool = True) -> None: ...
def find_theory(name: str, username: str = "master") -> Path: ...   # raises FileNotFoundError
```

`add_theory_path` clears the loader caches (`basic.theory_cache`,
`basic.item_index`) through a small hook in `basic`, so the next load sees the
new path. Calling it twice with the same directory has no further effect.

### Changes in `basic.py`

- `load_metadata` walks `theory_path(username)` and records, per theory name,
  the file it came from (first one wins). The cycle check spans all directories.
- `user_file(filename, username)` returns the file found on the path, or, if
  the name is not found, the path it returns today (so writers and error
  messages keep working). This changes behaviour (decision 8, approved): report every caller and list it in the changelog.
- Timestamps and `item_index` keep using the resolved file, so a theory with the
  same name in two directories is never confused.
- Where holpy *writes* a theory (`monitor.check_theory(rewrite=True)`), it
  writes to the file it read. Nothing ever writes inside an installed package
  unless `$HOLPY_LIBRARY_DIR` points there.

### Macros of external theories

Out of scope. A user theory that needs extra macros must import their Python
module first, as today. Note this in the README section (task A3).

## Tasks

### WS2-A: search path

| Step | Work |
|---|---|
| A1 | `_paths.py`: `theory_path`, `add_theory_path`, `find_theory`, with docstrings that state the order and the shadowing rule. |
| A2 | `basic.py`: metadata, file resolution and caches over the path, as above. |
| A3 | README: a "Your own theories" section with a three-line example. `AGENT-INSTRUCTION.md`: mention `HOLPY_THEORY_PATH` next to `HOLPY_LIBRARY_DIR`. |

**Tests** (`holpy/tests/paths_test.py` and `holpy/logic/tests/basic_path_test.py`;
every test uses a temporary directory and restores the environment and caches):

- `$HOLPY_THEORY_PATH` with two directories, plus the bundled library, gives that
  order from `theory_path()`; empty entries and a missing directory are skipped;
- a theory `mythy.json` in a temp directory that imports `nat` loads with
  `basic.load_theory('mythy')`, and a theorem stated in it can be retrieved;
- `add_theory_path` at run time, after a theory was already loaded, makes the new
  theory loadable (caches were cleared);
- a temp `nat.json` earlier on the path shadows the bundled one, and exactly one
  `WARNING` naming both files is logged (`assertLogs`);
- an import cycle across two directories raises `TheoryException`;
- with no path set, `theory_path()` is `[library_dir()]` and every existing test still passes.

**Acceptance checks.**

```bash
mkdir -p /tmp/thy && cat > /tmp/thy/mythy.json <<'EOF'
{"name": "mythy", "imports": ["nat"], "description": "test", "content": []}
EOF
HOLPY_THEORY_PATH=/tmp/thy python -c "
from holpy.logic import basic; basic.load_theory('mythy')
from holpy.kernel import theory; print(theory.thy.has_theorem('add_0_right'))"   # True
python -m unittest holpy.tests.paths_test holpy.logic.tests.basic_path_test
```

Also install the wheel in a clean venv (outside the checkout) and run the same
check there, so the bundled library is read from `site-packages`.

### WS2-B: no theory loading at import time

| Step | Work |
|---|---|
| B1 | Remove `basic.load_theory('interval_arith')` from `holpy/data/real.py` module level. Find what in `real.py` needs `interval_arith` loaded and load it there (lazily, once), or document that callers load it. |
| B2 | Inventory every other module-level `basic.load_theory(...)` outside tests. On `main`: `prover/omega.py` (`int`), `prover/auto/auto.py` (`topology`), `prover/simplex.py` and `prover/simplex_strict.py` (`real`), `prover/proofrec.py` (`smt`). For each, say whether importing it inside `load_theory_cache` can re-enter the loader. Fix only the ones that can, in the same way; list the rest in the report. |

**Tests.**

- `import holpy.data.real` does not change `theory.thy` (compare the object
  before and after);
- `basic.load_theory('real')` succeeds in a fresh process, and so does
  `basic.load_theory('interval_arith')` followed by `basic.load_theory('real')`;
- the tests in `holpy/data/tests/real_test.py` still pass (or fail exactly as
  in `docs/test_baseline.txt`).

**Acceptance checks.** The three tests above, and the full suite adds no line
to `docs/test_baseline.txt`. The report lists every caller that relied on the
import side effect and how it was changed.

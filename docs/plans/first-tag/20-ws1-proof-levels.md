# WS1: proof levels, `expand()` and `condense()`, and a condensed library

**Waves 1–2. Three agents in parallel (A, B, C), then one (D). The CLI (E) can go
with A or B.**

This replaces Phase A of the macro-proofs plan (2026-10-28). What changes
compared with that plan:

| Macro-proofs plan | This plan | Why |
|---|---|---|
| `slim(proof, keep_th=...)` | `condense(proof, to=Level.MACRO)` | Alex: one pair of verbs, by level |
| `rehydrate(proof)` | `expand(proof, to=Level.ANNOTATED)` | Alex: `expand` is the natural name |
| `expand(proof, depth=None, layout=...)` | `expand(proof, to=Level.PRIMITIVE)` | one level scheme for both |
| `keep_th="every:N"` | dropped | `annotated` covers "readable raw JSON" |
| `expand(depth=1)` on one line, for the web UI | `expand_line(...)`, deferred to the web-UI phase | a partly expanded *file* has no single level, see §2.3 |
| `layout="flat"` | `export_flat(...)`, export only, optional (B4) | a flat proof cannot be condensed back |

## 1. Background the agents need

A theorem item in a theory JSON looks like this (`holpy/library/nat.json`):

```json
{"name": "add_0_right", "ty": "thm", "prop": "x + 0 = x", "vars": {...},
 "num_gaps": 0, "attributes": [...],
 "steps": [ {"goal_id": "0", "method_name": "induction", ...}, ... ],
 "proof": [
   {"id": "0", "rule": "rewrite_goal", "args": "nat_plus_def_1, (0::nat) + 0 = 0",
    "prevs": [], "th": "⊢ (0::nat) + 0 = 0"},
   {"id": "1", "rule": "subproof", "args": "", "prevs": [], "th": "⊢ ∀n. ..."},
   {"id": "1.0", "rule": "variable", "args": "m, nat", "prevs": [], "th": "⊢ _VAR m"},
   ...
 ]}
```

- `steps` is the tactic script the web UI recorded. `proof` is the certificate.
- A `subproof` line has children with dot ids (`1.0`, `1.1`, …); its statement
  is its last child's statement. `Proof.insert_item` builds the tree from the ids.
- The checker (`Theory._check_proof_item`, `holpy/kernel/theory.py`) fills in a
  missing `th` (`seq.th = res_th`) and otherwise checks that the computed
  theorem proves the stored one.
- For a macro line, the checker either *evaluates* the macro (if
  `macro.level <= check_level`) or *expands* it with
  `Macro.expand(seq.id, args, prevs)` and checks the expansion. The expansion's
  children reference the macro line's `prevs` by id. It then throws the
  expansion away (`seq.subproof = None`).
- `parser.parse_proof_rule` reads `data['th']` and treats `""` as missing. A
  missing key is a `KeyError` today.
- `printer.export_proof_item` writes a line and, recursively, its subproof.
- Oracle macros have `level = 0` and no expansion. On `main` with `real`
  loaded these are: `int_const_ineq`, `int_eval`, `integer_simplex`,
  `nat_eval`, `real_compare`, `real_const_eq`, `real_const_ineq`,
  `real_eq_comparison`, `real_eval`, `real_norm`, `simplex_macro`, `sympy`, `z3`.

## 2. Design

### 2.1 Levels

```python
class Level(enum.IntEnum):
    MACRO = 1       # macro-level lines; `th` only where it is required (§2.4)
    ANNOTATED = 2   # macro-level lines; `th` on every line
    PRIMITIVE = 3   # every non-oracle macro line replaced by its expansion; `th` on every line
```

Higher means more expanded. `0` is left free (for a possible statement-only
"interface" level later; not part of this plan).

How each level is written in JSON:

- **MACRO.** As stored today, but the `th` key is *omitted* on lines that do
  not require it.
- **ANNOTATED.** As stored today: every line has `th`.
- **PRIMITIVE.** A macro line becomes a `subproof` line whose children are
  the expansion, and the original line is kept in an `expanded_from` key:

  ```json
  {"id": "2", "rule": "subproof", "args": "", "prevs": [], "th": "⊢ x + 0 = x",
   "expanded_from": {"rule": "apply_theorem_for",
                     "args": "nat_induct, {P: λx::nat. x + 0 = x, x: x}",
                     "prevs": ["0", "1"]}},
  {"id": "2.0", "rule": "theorem", ...},
  ...
  ```

  The kernel already checks `subproof` lines by checking their children, and the
  children may cite `0` and `1` by id. So a PRIMITIVE proof checks with no
  kernel change, and with every non-oracle macro unregistered. The parser
  ignores keys it does not know, so `expanded_from` is safe for old readers.

  Oracle lines (`z3`, …) stay as they are at every level, and `oracles()`
  reports them.

### 2.2 Functions (`holpy/proofs/`, new package)

```python
def expand(proof: list[dict], to: Level = Level.ANNOTATED, *, ctx: ProofContext) -> list[dict]: ...
def condense(proof: list[dict], to: Level = Level.MACRO, *, ctx: ProofContext) -> list[dict]: ...
def level_of(proof: list[dict], *, ctx: ProofContext) -> Level: ...
def oracles(proof: list[dict]) -> list[tuple[str, str]]: ...      # (line id, rule)

def expand_theory(data: dict, to: Level, *, steps: str = "keep") -> dict: ...
def condense_theory(data: dict, to: Level, *, steps: str = "keep") -> dict: ...
```

- `proof` is the JSON list of lines. Functions never modify their input.
- `ProofContext` carries what checking needs (the item's `vars`, and the theory
  loaded up to that item). The `*_theory` functions build it per item, the
  same way `monitor.check_theory` does.
- `steps="keep" | "drop"`: whether theorem items keep their `steps` key.
  `condense_theory(..., steps="drop")` is the only way to remove them. It exists for
  later; nothing in v0.1.0 calls it (decision 3). `expand_theory` never adds steps.
- Both `*_theory` functions set a top-level `"proof_level"` key to the
  resulting level's name (`"macro"`, …). It is a hint for humans and tools.
  Every function recomputes levels and never trusts the key.

### 2.3 What "idempotent" means here

Alex's rule: expanding a file that is already at least as expanded as asked
leaves it alone; condensing removes only what the target level does not need.
Line by line, that is:

- `expand(p, L)` only adds: it fills a missing `th` (if `L ≥ ANNOTATED`) and
  replaces unexpanded macro lines by `expanded_from` subproofs (if
  `L = PRIMITIVE`). Lines already at or above `L` are copied unchanged.
- `condense(p, L)` only removes: it collapses `expanded_from` subproofs back
  to their macro line (if `L ≤ ANNOTATED`) and drops `th` where not required
  (if `L = MACRO`). Lines already at or below `L` are copied unchanged.

`level_of(p)` is defined as the highest `L` with `expand(p, L) == p`. It is
the level of the least expanded line, so a file where only some macro lines
are expanded is `ANNOTATED`. Expanding it to `PRIMITIVE` expands the rest,
and condensing it to `ANNOTATED` collapses the expanded ones.

These properties are the core tests (WS1-A and WS1-B), on every stored proof of
`logic`, `nat` and `set` (and in WS1-D, the whole library):

| # | Property |
|---|---|
| P1 | `expand(expand(p, L), L) == expand(p, L)` and `condense(condense(p, L), L) == condense(p, L)` |
| P2 | if `level_of(p) ≥ L` then `expand(p, L) == p`; if `level_of(p) ≤ L` then `condense(p, L) == p` |
| P3 | round trip: if `p == condense(p, L0)`, then `condense(expand(p, L), L0) == p` for every `L ≥ L0` |
| P4 | checking `expand(p, L)` and `condense(p, L)` gives the same theorem as checking `p` |
| P5 | `level_of(expand(p, L)) ≥ L`; `level_of(condense(p, L)) ≤ max(L, level_of of the required-th lines)` |
| P6 | a `PRIMITIVE` proof checks with every non-oracle macro removed from `theory.global_macros` |

Equality is equality of the JSON values (lists of dicts), and byte equality
after the canonical writer (§2.5).

### 2.4 Which lines keep `th` at MACRO

A line *requires* `th`, and keeps it at every level, when:

1. it is the last top-level line (the theorem's statement), or
2. its rule is `sorry` (a gap has nothing else to give its statement), or
3. its theorem is on the **guard list** (below).

The prototype showed that blanking `th` works for `logic` and `nat` but not for
all of `set`: `nat_finite` takes 198 s instead of under one second, and one
more theorem fails. The cause is not known yet (the log shows a term-parsing
message, so `th` may give later lines their parsing context). So:

- **Guard.** `condense_theory(..., to=MACRO)` checks each condensed theorem. If it
  no longer checks, gives a different statement, or needs more than 1.5× the
  kernel steps (`ProofReport.steps`) of the annotated version, the theorem is
  written at `ANNOTATED` instead, and the theorem goes on a guard list returned
  in the result and written to the log. Kernel steps are used instead of time
  so the result is deterministic.
- **Investigation (WS1-A3).** Find which lines in `nat_finite` need their `th`,
  and turn that into a rule for case 3 (by rule name or by a structural
  test). If the rule is found, the guard should only trigger in a handful of
  theorems in the whole library.

### 2.5 Canonical writer

`holpy/proofs/jsonio.py`:

```python
def dumps_theory(data: dict) -> str: ...
def write_theory(path: str | os.PathLike, data: dict) -> None: ...
```

- Valid JSON, UTF-8, `ensure_ascii=False`, keys sorted, no trailing whitespace,
  final newline.
- The top-level keys on their own lines. Each `content` item on one line,
  except that each `proof` line (and each `steps` entry) gets its own line, so
  git diffs stay readable per proof line.
- Separators `", "` and `": "` inside a line. *(The compact `","`/`":"` saves
  about 5% more. Fine either way; pick one and keep it.)*
- `dumps_theory(json.loads(dumps_theory(d))) == dumps_theory(d)`.
- `holpy/server/monitor.py` (`rewrite=True`) and `holpy/syntax/json_output.py`
  switch to `write_theory`, so holpy never writes `indent=4` again.

## 3. Tasks

### WS1-A: level core (`MACRO` ⇄ `ANNOTATED`), writer, parser

*Starts from `main` after PR #2 is merged.*

| Step | Work |
|---|---|
| A1 | `parser.parse_proof_rule`: a missing `th` key means "no statement" (as `""` does today). `printer.export_proof_item` unchanged. Everywhere in `holpy.proofs`, a missing `th` and `"th": ""` are the same thing (downstream builders already write `""`); `condense` writes the key out as missing, never as `""`. |
| A2 | `holpy/proofs/` with `Level`, `ProofContext`, `expand`/`condense`/`level_of` for `MACRO` and `ANNOTATED`, the `*_theory` functions, the guard and `steps=`. `PRIMITIVE` raises `NotImplementedError` until WS1-B lands. |
| A3 | Investigation of `set.nat_finite` (§2.4). Deliverable: a short note in the PR naming the lines that need `th` and why, and the rule added for case 3, or "not found" with what was tried. |
| A4 | `holpy/proofs/jsonio.py` (§2.5); `monitor.py` and `json_output.py` use it. |

**Tests** (`holpy/proofs/tests/levels_test.py`, `jsonio_test.py`):

- P1–P5 for `MACRO`/`ANNOTATED` on every stored proof in `logic`, `nat`, `set`;
- a proof line without a `th` key parses (A1);
- the guard: a hand-made proof that only checks with an intermediate `th` (or
  `nat_finite` itself) comes back `ANNOTATED`, and it is on the guard list;
- `steps="drop"` removes `steps` and nothing else; `steps="keep"` changes nothing;
- the writer: round-trip on every library file, and `json.loads` of the output
  equals `json.loads` of the input;
- `dumps_theory` of a theory with a non-ASCII statement (`∀`, `⊢`) writes the characters, not `\u` escapes.

**Acceptance checks.**

```bash
python -m unittest holpy.proofs.tests.levels_test holpy.proofs.tests.jsonio_test
python -c "
import json; from holpy.proofs import condense_theory, Level
from holpy.proofs.jsonio import dumps_theory
d = json.load(open('holpy/library/nat.json'))
print(len(json.dumps(d, indent=4)), len(dumps_theory(condense_theory(d, Level.MACRO))))"
# expect about 2.0 MB -> under 0.7 MB
```

### WS1-B: `PRIMITIVE`: expansion into the file

*In parallel with A, against A's interface. Rebase on A once it merges.*

| Step | Work |
|---|---|
| B1 | `expand(p, PRIMITIVE)`: for each macro line that is not an oracle, call `Macro.expand(id, args, prevs)` (exactly as the checker does), print the result with `printer.export_proof_item`, recurse into the new lines until only primitive rules, `theorem`, `variable`, `assume`, `sorry`, `subproof` and oracle lines remain, and wrap the result as in §2.1. |
| B2 | `condense(p, L ≤ ANNOTATED)` for `expanded_from` lines: restore `rule`, `args` and `prevs`, keep `th`, drop the children. |
| B3 | `oracles(p)`: the ids and rules of oracle lines, at any level. |
| B4 | *(Optional, only if A–C are done.)* `export_flat(p)`: one list without subproofs, renumbered, for external checkers. Export only; `condense` and `level_of` reject it. |

**Known risk.** Printed expansions must parse back. A term printed without type
annotations may not parse in the item's context, for example a fresh variable
that an expansion introduces. `holpy.syntax.settings` has no option for explicit types today
(only `unicode`, `highlight` and `line_length`), so do not invent a workaround:
list every macro and line that fails to round-trip in the report, and stop.
Print with `global_setting(unicode=True, highlight=False)`, as
`monitor.check_theory` does, so the output matches the library's notation.

**Tests** (`holpy/proofs/tests/primitive_test.py`):

- P1–P6 at `PRIMITIVE` on `logic` (all theorems) and on 20 theorems of `nat`
  (fixed list, chosen to cover each macro used in `nat`);
- for each new macro of PR #2 (if merged), one theorem from its own tests:
  expand to `PRIMITIVE`, check with all non-oracle macros removed, condense to
  `MACRO`, compare with the original;
- a proof with a `z3` line: the line survives `PRIMITIVE` unchanged and `oracles()` reports it.

**Acceptance checks.** (The CLI lines need WS1-E. Until it merges, run the same
steps through the Python functions.)

```bash
python -m unittest holpy.proofs.tests.primitive_test
python -m holpy.proofs expand --to primitive holpy/library/logic.json -o /tmp/logic_p.json
python -m holpy.proofs check --no-macros /tmp/logic_p.json        # every theorem ok, oracles listed
python -m holpy.proofs condense --to macro /tmp/logic_p.json -o /tmp/logic_m.json
python -m holpy.proofs condense --to macro holpy/library/logic.json -o /tmp/logic_m2.json
cmp /tmp/logic_m.json /tmp/logic_m2.json                          # identical
```

### WS1-C: the macro contract test

`holpy/macros/tests/macros_contract_test.py`, from the macro-proofs plan, with
the oracle list measured on `main`:

```python
ORACLES = {"int_const_ineq", "int_eval", "integer_simplex", "nat_eval",
           "real_compare", "real_const_eq", "real_const_ineq",
           "real_eq_comparison", "real_eval", "real_norm", "simplex_macro",
           "sympy", "z3"}
```

After importing every module that registers macros (`holpy.logic.basic`
loading `real`, `holpy.data.{nat,integer,expr}`, `holpy.prover.{z3wrapper,simplex,sympywrapper}`,
`holpy.macros`), for every name in `theory.global_macros`:

1. if it is not in `ORACLES`: `get_proof_term` is overridden, and `level` is `None` or `≥ 1`;
2. if it is in `ORACLES`: `level == 0` (so the list cannot go stale silently);
3. its `sig` round-trips through `printer.print_str_args` and `parser.parse_args`
   on at least one real argument, taken from a library proof line or from the macro's own tests;
4. the expansion graph is well-founded: record which macros each expansion
   uses (from the library proofs expanded in WS1-B's tests) and assert the
   graph has no cycle.

Also, any macro registered but never used in the library or a test is listed
in the test output, so missing coverage is visible.

**Acceptance checks.** `python -m unittest holpy.macros.tests.macros_contract_test`
passes, and the PR lists any macro that fails a rule. Do not fix a failing
macro in this task: report it.

### WS1-D: condense the bundled library

*Wave 2. Needs WS0, WS1-A, and every WS3 PR merged.*

1. `python -m holpy.proofs condense --to macro --steps keep holpy/library/*.json --in-place`
   (`--steps keep`; decision 3: steps are never dropped in v0.1.0).
2. Re-check with `scripts/check_library.py`, compare with the WS0 baseline
   re-run under the fixed kernel: **no theorem changes status or statement.**
   Theorems quarantined by WS3 stay as they are (a gap); condensing never touches `docs/quarantine/`.
3. Commit the JSON as its own commit: "library: condense to macro level".
   No other change in that commit.
4. Report: size per file before and after, the guard list, total check time
   before and after.

**Acceptance checks.**

```bash
du -sh holpy/library                                    # about 6.3 MB with steps kept
python scripts/check_library.py --out /tmp/after.tsv
python scripts/check_library.py --compare docs/library_check.tsv /tmp/after.tsv   # exit 0
python -m build --wheel && ls -l dist/*.whl
```

### WS1-E: CLI

`python -m holpy.proofs {expand,condense,level,check} FILE... [--to LEVEL]
[--steps keep|drop] [-o OUT | --in-place] [--no-macros]`

- `level` prints the level of each file and a histogram of theorem levels.
- `check` checks stored proofs (reusing WS0's code), and with `--no-macros`
  checks with all non-oracle macros removed.
- Theory files are found through the WS2 search path when given by name, and
  as paths when they end in `.json`.

Tests: one test per subcommand on a temporary copy of `logic.json`.

## 4. Reconciliation with the condensing report

Alex uploaded `json-size-and-proof-efficiency-2026-10-27.md` after the first
version of this plan. It analyses a downstream project (23 theories, 51.8 MB)
built on this library. Each of its ideas, and where it ends up:

| Report item | Where it lands |
|---|---|
| 2a: keep `th` only on the last line; compact writer (16% on its own) | `MACRO` level and the canonical writer (A2, A4). The report found 2× faster checking and 4 of 4 theories re-checking. Our prototype on the bundled library agrees for `logic` and `nat` but not for `set` (§2.4), so the guard and A3 stay. When A3 finds the cause, tell the downstream project, which blanks `th` on its own. |
| F1: an exporter option to omit `th` | No new option on `ProofTerm.export`. Downstream builders call `condense_theory`/`condense` on what they export. One mechanism, not two. |
| F2: `apply_induct` cannot round-trip; draft `induct.py` is broken | Done in PR #2 (`induct`, `parse_args` for `Tuple[str, Term, Term]`). WS1-C's contract test keeps it fixed. |
| F3 `ereal_cases`, F4 `semiring_norm`, F5 structural macros, F6 `nat` linear arithmetic | PR #2 holds `cases`, `semiring_norm`, `exI_list`/`conj_*`/`contr`, `transfer`, `real_linarith` and `nat_linarith`. WS1-C and WS1-B test that they expand. Anything further (the three-constructor `ehat` case, retiring the remaining `z3` calls) is not part of v0.1.0. |
| 2b: emit `beta_norm` / `apply_theorem_for` instead of congruence trees | A change in the downstream builders, not in holpy. Nothing to do here. |
| Section 3: agent proof style; builders' copied helpers | Downstream project only. |
| Trust story: every macro is level 1 and expands on check | The contract test (WS1-C) enforces it for holpy's own macros, and `oracles()` (B3) lists the exceptions in any proof. |
| What downstream needs from holpy: a theory search path, no import-time loading | WS2. A tag before the downstream project switches: WS5-C. |

Not done in v0.1.0, and noted so it is not lost: a "transport certificate"
per theory (oracle steps plus cited theorems that are stored without a proof),
which the downstream plan calls C3. `oracles()` is its first half.

## 5. Not in this workstream

- The web UI, `expand_line`, `insert_item` and anything else from Phase E.
- New macros (Phase D). PR #2 holds those.
- The project-side switch (Phase C) and the proof-cost lints (Phase F).

# WS4: land the style branches with the review fixes

**Wave 1. Up to seven agents, one per branch. Kernel first, then logic and
imperative (which are stacked on kernel), the rest in any order.**

## Brief

The first DeepSeek pass produced seven `style/*` branches (documentation,
annotations, `from __future__`, `logging`). None is merged. Each was reviewed on
2026-10-22; the reviews are in the project files under `Feedback 28-Oct/`,
one per branch, and each task below repeats what must be done.

For every branch:

1. Create `ft/ws4-<pkg>` from `main` and bring the branch's own commits over
   (`git rebase --onto main <old base> style/<pkg>` or cherry-pick). The
   branches are two commits behind `main` and carry their own copies of the
   two `chore`/`docs` commits that are already on `main`
   ("keep local agent setup out of the public repository", "document the
   local untracked instruction file"): **drop those copies**.
2. Apply every row of the review's findings table, unless the task below says
   otherwise. Documentation fixes go in one commit per file or per topic.
3. A finding that is a **code** change (a bug fix, a removed import, a
   reordered check) goes in its **own commit with a test**, never inside a
   docstring commit.
4. Do not change behaviour beyond what the task lists. Where a review says
   "fix separately", the task says whether that happens here or is deferred.
5. Check each docstring you write against the code by running it, as the
   reviews did. A docstring that is merely plausible is the failure mode
   these reviews found.
6. Deliverable: one PR per branch, `[WS4-<pkg>] Land style/<pkg> with review fixes`.
   The report's "Changes" table has one row per review finding, with its status
   (fixed / deferred, with the reason).

Shared acceptance checks for every WS4 PR:

```bash
git log --oneline main..HEAD          # no copies of main's chore/docs commits
ruff check holpy/<pkg>                # no findings beyond those the review accepted
pytest holpy -q -p no:cacheprovider --continue-on-collection-errors -rfE   # adds no line to docs/test_baseline.txt
python - <<'EOF'                      # only the listed code commits change the AST
# compare ast.dump of every .py file in holpy/<pkg> between main and HEAD,
# excluding docstrings; print the files that differ
EOF
```

The AST script is part of WS4-kernel's deliverable
(`scripts/ast_diff.py BASE HEAD PATH`), and the other WS4 agents use it. Until it
lands, each agent runs an inline copy.

---

## WS4-kernel (first)

Review: *style kernel — documentation review.md*. The ten earlier findings are
fixed in `b452f883`. What remains:

| Where | Do |
|---|---|
| `thm.py` module docstring | "Theorems can only be built by the primitive rules below, which are intended to be sound." |
| `term.py` `occurs_var`, `subst`; `theory.py` `checked_extend`, `check_proof` | Document the current limitations exactly as the review says. WS3 rewrites these sentences when it fixes the bugs; that is expected. |
| `docs/kernel-style-modernization.md` | "0 errors, 127 warnings", and fix the "no annotation changes" claim. |
| Annotation mismatches (`subst_type_inplace -> None`, `get_sorrys -> list[Thm \| None]`, `check_proof -> Thm \| None`, `get_proof_term(prevs: Sequence[ProofTerm])`, `server.py:56 prevs`) | Fix the annotations to match the code. Annotations only: no logic change. |
| `type.py` attribute declarations, `__eq__(self, other: object)` | Declare the attributes and widen `__eq__`, if it changes no runtime behaviour (a class-level annotation without a value does not). Otherwise defer. |

Extra deliverable: `scripts/ast_diff.py`.

**Specific check.** `scripts/ast_diff.py main HEAD holpy/kernel` reports no file.

## WS4-logic (after kernel)

Review: *style logic — documentation review.md*.

| Where | Do |
|---|---|
| `imp_conj_macro`, `sub_conv`, `strip_disj`, `strip_conj` | Docstrings as the review says. |
| 56 copied `get_proof_term` docstrings | Delete them (the base class documents the method), except where you replace one with a description of that construction. |
| `auto.py` `debug_auto` | Document that output goes to `logging.debug`. |
| `auto_macro.get_proof_term(args, pts)` renamed to `(args, prevs)` | **Revert the rename** (keyword callers break; decision 8, approved). |
| `basic.py` `load_metadata` | **Restore** the `os.path.getmtime(...)` call (its removal silently changed a failure mode). |
| Unused imports in `tactic.py` (`Any`, `copy`, `TyInst`) and `logic.py` (`term`) | Remove, in a separate commit. Check each for a registration side effect first. |

## WS4-macros

Review: *style macros — documentation review.md*. **Most of this branch is
overtaken by PR #2**, which rewrites `holpy/macros/induct.py` and replaces
`InductMacro`.

- PR #2 is merged (decision 1): do not rebase `style/macros`. Start from `main` and
  (a) change `holpy/macros/__init__.py` to absolute imports
  (`from holpy.macros import induct  # noqa: F401`, …); (b) give every module in
  `holpy/macros/` a module docstring and `__all__`, checked against the code;
  (c) correct the `Raises` clauses of `induct` (it raises `TheoryException`
  from `theory.get_theorem` and `MatchException` from the matcher, not
  `KeyError`), checked by test; (d) fix or remove the pointer to
  `docs/tutorial/macros.ipynb`. Close `style/macros` unmerged, with a note.

## WS4-util

Review: *style util — documentation review.md*.

| Where | Do |
|---|---|
| `Monomial.__le__` | Keep the change, as its **own commit titled as a bug fix**, with a test showing `a <= a` is `True` and `sorted` of coefficients 3, 1, 2 gives 1, 2, 3. Run the library check on `nat`, `real`, `int` and report any change (decision 8, approved). |
| `Monomial.__mul__`, `collect_pairs` (example and key requirement), `Monomial` class docstring, `typecheck.checkinstance` | Docstrings as the review says. Replace the `collect_pairs` example with one that runs, and add it as a doctest or unit test. |
| `compare_fst` (only the first factor is compared) | **Document only** ("sorted up to ties"). The fix changes polynomial ordering and is deferred past v0.1.0. Add an `expectedFailure` test that shows `Polynomial([x, x^2]) == Polynomial([x^2, x])` is `False`, referencing a new GitHub issue you draft in the report (do not open it yourself). |

## WS4-geometry

Review: *style geometry — documentation review.md*.

| Where | Do |
|---|---|
| `Line.combine`, `Circle.combine` | `-> None`, "Merge the points of `other` into this line in place", fix the note. |
| `check_redundant`, `is_same_line`, `__repr__`, `GeometryTransformer.circle` | Docstrings as the review says. |
| Comments before docstrings | Move below the docstring. |
| `Circle.__eq__` reads `other.center` before `isinstance` | Own commit with a test: comparing a `Circle` with a non-`Circle` returns `False` instead of raising. |
| `Fact.__init__` ignores `tail` | Document only. The fix (`self.tail = tail`) changes prover behaviour; list it under "Found, not fixed" with a one-paragraph analysis of where `tail` is read. |

## WS4-imperative (after kernel)

Review: *style imperative — documentation review.md*.

| Where | Do |
|---|---|
| 67 placeholder docstrings | Delete, or replace with what the node or grammar production does. Report the count of each. |
| `imp.py` constructor helpers (`comT`, `Skip`, …) | "Return the constant `Skip` at command type `T`" and similar. |
| `imp.py` macro and tactic `get_proof_term` | Name the construct. |
| `ArrayElt.convert_hol`, `Field.convert_hol` bug fixes | Move to their **own commit**, each with a test in `holpy/imperative/tests` that fails on `main`. |
| `imp.py` `from holpy.prover import z3wrapper` | It registers macros: keep it, mark `# noqa: F401  (registers macros)`. |

## WS4-paraverifier

Review: *style paraverifier — documentation review.md*.

| Where | Do |
|---|---|
| `docs/paraverifier-style-modernization.md` | Remove the claim about a package docstring, or add the docstring to `paraverifier/__init__.py`. |
| Module docstring, `load_system`, `get_proof`, `load_hints`, `ParaSystem` | As the review says. `get_proof`'s docstring states that it is incomplete and returns `None`. |
| `ParaSystem.__init__` `rules` annotation | `list[tuple[Var \| list[Var], Term, dict]]`, and describe the fields. |

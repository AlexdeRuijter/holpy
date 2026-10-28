# Rules for every agent on the first tag

These rules apply to every lead agent and sub-agent. They add to
`AGENT-INSTRUCTION.md` in the repository root, which you must also read. Where
the two differ, `AGENT-INSTRUCTION.md` wins, and you say so in your report.

## 1. Before you start

1. Read `AGENT-INSTRUCTION.md`, [00-overview.md](00-overview.md) and your
   workstream file completely. Read the code a task names before changing it.
2. Set up:
   ```bash
   python -m venv .venv && . .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Record the starting state, so your report can show the change:
   ```bash
   pytest holpy -q -p no:cacheprovider --continue-on-collection-errors 2>&1 | tail -1
   ```
   and, once WS0 has merged, the library baseline for the theories your task touches
   (see [10-ws0-baseline.md](10-ws0-baseline.md)).

## 2. Scope

- Do only your task. If you find something else broken, write it under
  "Found, not fixed" in your report. Do not fix it.
- **Never** skip, delete, weaken or `xfail` a test to make a run pass, unless
  your task says so explicitly.
- **Never** change a public name, signature, default, or return type unless the
  task says so. If the task cannot be done without one, stop and report.
- **Kernel** (`holpy/kernel/`): only WS3 changes kernel behaviour, and only as
  its tasks describe. Everyone else may change kernel docstrings and
  annotations only, as `AGENT-INSTRUCTION.md` requires.
- **Library JSON** (`holpy/library/*.json`) is a set of certificates. Only
  WS1-D rewrites it, and only through the tools WS1 builds. A hand edit to a
  JSON file needs its own commit that names the theorem and the reason.

## 3. Branches, commits and PRs

- Branch from `main` (or from the branch your task names) as
  `ft/<ws>-<task>-<short-name>`, for example `ft/ws3-4-subst-closed`.
- One logical change per commit. Packaging, style and behaviour changes are
  separate commits. A bug fix found during a documentation task is its own
  commit, with a test.
- Commit message: `<area>: <what changed>` in the imperative, then a body that
  says why.
- One PR per task, against `main`, titled `[WS<n>-<task>] <what>`. The PR body
  is your report (§5).

## 4. Code standards

From `AGENT-INSTRUCTION.md`, repeated because they are the most often missed:

- Absolute imports (`from holpy.kernel.term import Term`), never relative.
- New and refactored code: `from __future__ import annotations`, full type
  annotations, NumPy-style docstrings (`Parameters` / `Returns` / `Raises`),
  `logging` instead of `print`.
- A docstring states what the code *does*. If you are not sure, run it. A
  placeholder docstring ("Initialize this object.") is worse than none.
- Ruff: `ruff check holpy` must not report new findings in files you touched.
- Tests are `*_test.py` next to the code (`holpy/<pkg>/tests/`), and use
  `unittest.TestCase` so both `pytest` and `python -m unittest` run them.
  Do not name a helper function `test_*`.

## 5. The report (your PR body)

```markdown
## Task
WS<n>-<task>: <title from the workstream file>

## Changes
| File | Symbol | Change | Behaviour change? |
|---|---|---|---|

## Tests
- Added: <test file::test name> — what it checks
- Suite before: <passed/failed/errors>   after: <passed/failed/errors>
- Newly failing tests: none | <list with reason>

## Library check (if the task can affect proof checking)
- Theories checked: <list or "all">
- Before → after: <ok/fail counts>, theorems that changed status: none | <list>
- Check time before → after: <seconds>

## Acceptance checks
<each check from the workstream file, the command, and its actual output>

## Found, not fixed
<anything out of scope you noticed>

## Questions for Alex
<anything that needs a decision; "none" if none>
```

## 6. When to stop and ask

Stop, push what you have to your branch, and put the question in your report when:

- a test you did not write starts failing and you do not know why;
- a bundled theorem stops checking (any task);
- the task needs a public API change, or a kernel behaviour change outside WS3;
- the workstream file and the code disagree about how something works.

## 7. Sub-agents

A lead agent may hand a task to a sub-agent. Give the sub-agent this file, the
overview, its workstream file, and the task ID. The lead agent reviews the
sub-agent's branch against the task's acceptance checks before opening the PR,
and stays responsible for the report.

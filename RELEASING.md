# Releasing holpy

**An agent never uploads to TestPyPI or PyPI and never creates or pushes a
tag.** Those steps are done by Alex only. Agents prepare and verify; Alex
uploads and tags.

This is the procedure for `v0.1.0`. Run every command from a clean checkout of
`main`, not from a branch with uncommitted changes. Build and upload the same
commit that you tag.

## 1. Preconditions

- CI is green on the commit to release, including the `package` job in
  `.github/workflows/ci.yml`. That job runs `python -m build`,
  `twine check dist/*`, installs the built wheel in a fresh venv and runs the
  import and `basic.load_theory("real")` smoke test.
- `git status --short` prints nothing.
- PyPI and TestPyPI accounts have an API token for the `holpy` project. Use
  `__token__` as the username and the token as the password when twine asks.
- `python` is Python 3.12 with `build` and `twine` installed
  (`pip install build twine`).

## 2. Build and inspect

```bash
rm -rf dist build
python -m build
python -m twine check dist/*
python -m zipfile -l dist/holpy-0.1.0-py3-none-any.whl > /tmp/holpy-wheel.txt
grep -q 'holpy/library/logic.json' /tmp/holpy-wheel.txt
grep -q 'holpy/data/real.py' /tmp/holpy-wheel.txt
! grep -q '/tests/' /tmp/holpy-wheel.txt
```

`twine check` must report `PASSED` for the sdist and the wheel. The last four
commands must exit 0; the final one checks that the wheel contains no test
files. The wheel must contain the bundled `holpy/library/*.json` theories and
the `holpy/data` modules. Do not continue if any check fails.

## 3. Upload to TestPyPI

```bash
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

At the prompts, enter `__token__` and the TestPyPI API token. Then install the
published files, not the local `dist/` directory, in a clean venv outside the
checkout. The extra index lets pip fetch lark, sympy and z3-solver from PyPI.

```bash
rm -rf /tmp/holpy-testpypi
python -m venv /tmp/holpy-testpypi
/tmp/holpy-testpypi/bin/pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple holpy==0.1.0
(
  cd /tmp
  /tmp/holpy-testpypi/bin/python -c "import holpy; print(holpy.__version__)"
  /tmp/holpy-testpypi/bin/python -c "from holpy.logic import basic; basic.load_theory('real')"
  /tmp/holpy-testpypi/bin/python -c "from holpy.proofs import Level, condense, expand"
)
```

The first command prints `0.1.0`; the other two print nothing and exit 0. If
any command fails, stop. Fix the problem, bump the version if the files already
exist on TestPyPI, and start again from step 2.

## 4. Upload to PyPI

```bash
python -m twine upload dist/*
```

At the prompts, enter `__token__` and the PyPI API token. Uploading is
permanent: a version cannot be replaced. If the upload is wrong, see step 6.

## 5. Tag and push

Create a signed tag on the commit that was built and uploaded, then push it:

```bash
git status --short      # must print nothing
git rev-parse HEAD      # record this commit
git tag -s v0.1.0 -m "holpy 0.1.0"
git verify-tag v0.1.0
git push origin v0.1.0
```

Do not use a lightweight tag if signing fails; fix the Git signing setup first.
Do not move or delete a tag whose version is still on PyPI.

## 6. Yanking a bad release

There is no twine command for yanking. Use the PyPI web interface:

1. Sign in at <https://pypi.org>.
2. Open **Your projects** → **holpy** → **Manage** → **Releases**.
3. Select release **0.1.0**, choose **Yank release**, and give the reason.
4. Confirm the release is marked as yanked.

Yanking keeps the files but removes the release from normal resolution. An exact
pin such as `pip install holpy==0.1.0` can still install it, so publish a fixed
release with a new version (for example `0.1.1`). Yanking can be undone from the
same page, but the version number cannot be reused. Leave the `v0.1.0` tag in
place unless the source itself is also being withdrawn; it identifies the source
that was uploaded.

If the bad files must be removed completely, use the PyPI web interface to
delete the release, then decide with the maintainers whether to delete the tag.
Do not reuse `0.1.0` after deletion.

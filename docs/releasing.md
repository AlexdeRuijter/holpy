# Releasing holpy

Pushing a tag `vX.Y.Z` (for example `v0.1.0`) runs `.github/workflows/release.yml`:
tests on Python 3.10–3.13, build of sdist and wheel, a clean-install smoke test, then
upload to PyPI. The tag must equal `v` + the `version` in `pyproject.toml`, otherwise
the build job fails before anything is published.

## One-time setup

1. On pypi.org, log in and go to *Your projects → Publishing* (for a name that does not
   exist yet: <https://pypi.org/manage/account/publishing/> → "Add a new pending publisher").
   Add a GitHub publisher with:
   - PyPI project name: `holpy`
   - Owner: `AlexdeRuijter`
   - Repository: `holpy`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
2. On GitHub, *Settings → Environments → New environment*, named `pypi`. Optionally add
   yourself as required reviewer so each publish needs one click of approval.

## Releasing

```
# bump version in pyproject.toml (and holpy/__init__.py if it is duplicated), merge to main
git tag v0.1.0
git push origin v0.1.0
```

PyPI versions can never be re-uploaded. If a release fails after upload, bump the version.
Optional dry run: publish to TestPyPI first by registering a second trusted publisher there.

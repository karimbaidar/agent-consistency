# Contributing

Thanks for helping make `agent-consistency` more reliable.

## Pull Requests

External contributors should work through pull requests. A PR should include:

- a clear problem statement
- focused code changes
- tests or docs for changed behavior
- passing `tests`, `docs`, and `false-success scan` GitHub Actions

The intended main-branch rule is:

- require a pull request before merge
- require at least one approving review
- dismiss stale approvals when new commits are pushed
- require the current CI checks before merge
- allow the repository owner to bypass in emergencies

GitHub currently reports that branch protection for this private repository
requires GitHub Pro or making the repository public. Until that account-level
condition changes, treat this file as the contribution policy and keep changes
reviewable.

## Local Validation

```bash
python -m pip install -e ".[dev,docs]"
ruff check src tests examples benchmark
python -m pytest --cov=agent_consistency --cov-report=term-missing
mkdocs build --strict
scripts/check_no_secrets.sh
```

## Releases

Package publishing is automated from `.github/workflows/publish.yml`.

To publish a new package:

1. Update the version in `pyproject.toml`.
2. Open and merge an approved PR to `main`.
3. Confirm the `publish` workflow built the distributions.
4. If the version does not already exist on PyPI, the workflow publishes through
   PyPI Trusted Publishing.

PyPI versions are immutable. If `pyproject.toml` still has an already-published
version, the workflow skips publishing instead of failing.

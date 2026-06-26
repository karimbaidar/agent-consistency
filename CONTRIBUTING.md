# Contributing

Thanks for helping make `agent-consistency` more reliable.

## Pull Requests

External contributors should work through pull requests. A PR should include:

- a clear problem statement
- focused code changes
- tests or docs for changed behavior
- a `pyproject.toml` version increase
- passing `tests`, `version-bump`, `docs`, and `false-success scan` GitHub Actions

The `main` branch rule is:

- require a pull request before merge
- require at least one approving review
- dismiss stale approvals when new commits are pushed
- require the current CI checks before merge
- allow the repository owner to bypass in emergencies

Direct owner maintenance is allowed for release operations, but contributors
should work through reviewed pull requests.

## Local Validation

```bash
python -m pip install -e ".[dev,docs]"
ruff check src tests examples benchmark
python -m pytest --cov=agent_consistency --cov-report=term-missing
scripts/check_version_bump.sh origin/main..HEAD
mkdocs build --strict
scripts/check_no_secrets.sh
```

## Releases

Package publishing is automated from `.github/workflows/publish.yml`.

Every contribution must increase `[project].version` in `pyproject.toml`; keep
`agent_consistency.__version__` in sync. To publish a new package:

1. Update the version in `pyproject.toml`.
2. Update `src/agent_consistency/__init__.py` to the same version.
3. Open and merge an approved PR to `main`.
4. Confirm the `publish` workflow built the distributions.
5. If the version does not already exist on PyPI, the workflow publishes through
   PyPI Trusted Publishing.

PyPI versions are immutable. If `pyproject.toml` still has an already-published
version, the workflow skips publishing instead of failing.

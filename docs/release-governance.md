# Release Governance

`agent-consistency` is the canonical Python package. The False Success Lab is a
separate demo app and should not be published as a Python package.

## PyPI Publishing

Publishing is automated by `.github/workflows/publish.yml`.

The workflow runs on pushes to `main`, manual dispatch, and published GitHub
releases. It always builds and checks the package artifacts. It publishes only
when the version in `pyproject.toml` does not already exist on PyPI.

This keeps the main branch honest without trying to overwrite immutable PyPI
files.

Every contribution must bump `[project].version` in `pyproject.toml` and keep
`agent_consistency.__version__` in sync. CI enforces this through
`scripts/check_version_bump.sh`.

## Trusted Publisher Setup

Configure PyPI Trusted Publishing for the existing `agent-consistency` project:

- owner: `karimbaidar`
- repository: `agent-consistency`
- workflow: `publish.yml`
- environment: `pypi`

No `PYPI_TOKEN` secret is required. The publish job uses GitHub OIDC with
`id-token: write`.

If the PyPI project does not exist yet, create a pending trusted publisher for
the same owner, repository, workflow, environment, and project name:
`agent-consistency`.

## Branch Protection Target

The `main` branch rule is:

- require pull requests before merging
- require one approving review
- dismiss stale approvals
- require status checks:
  - `tests`
  - `version-bump`
  - `docs`
  - `false-success scan`
- block force pushes
- allow the owner to bypass only for emergency maintenance

Branch protection is applied now that the repository is public. The owner can
bypass for emergency release maintenance; external contributors should use
reviewed pull requests.

## Contributor Flow

Contributors should open PRs. Maintainers should merge only after review and
green checks. Version bumps should be explicit so automatic PyPI publication is
predictable.

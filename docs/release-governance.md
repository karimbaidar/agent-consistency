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

The intended `main` branch rule is:

- require pull requests before merging
- require one approving review
- dismiss stale approvals
- require status checks:
  - `tests`
  - `docs`
  - `false-success scan`
- block force pushes
- allow the owner to bypass only for emergency maintenance

GitHub currently reports that branch protection for this private repository
requires GitHub Pro or making the repository public. Once one of those is true,
apply the rule in GitHub repository settings.

## Contributor Flow

Contributors should open PRs. Maintainers should merge only after review and
green checks. Version bumps should be explicit so automatic PyPI publication is
predictable.

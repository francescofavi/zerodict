# Development

## Purpose

Setup instructions for contributors: installing the project locally, running the quality pipeline, running tests, and running examples.

## Scope

Covers local development workflow plus the release/publish workflow split. Releases are automated via [release-please](https://github.com/googleapis/release-please) on `main`, while publishing to PyPI is a manual `workflow_dispatch` step gated by a protected GitHub environment (Trusted Publishing / OIDC).

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- `git`

### Install uv

**Linux / macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Clone and Setup

```bash
git clone https://github.com/francescofavi/zerodict.git
cd zerodict
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

> All commands (`uv sync`, `uv run`) work identically on Linux, macOS, and Windows.

---

## Running Tests

```bash
uv run pytest
```

With coverage report:

```bash
uv run pytest --cov=zerodict --cov-report=term
```

Verbose output:

```bash
uv run pytest -v
```

Run a single test:

```bash
uv run pytest tests/test_zerodict.py::TestZeroDict::test_basic_creation
```

---

## Quality Pipeline

The repository ships four static analysis tools, all configured in `pyproject.toml`. The pre-commit hook runs the same set on each commit; CI runs them on every PR.

### Ruff — lint and format

```bash
uv run ruff check src/                    # lint
uv run ruff check --fix src/              # lint with auto-fix
uv run ruff format src/                   # apply formatting
uv run ruff format --check src/           # verify formatting without changes
```

Configured rule set: `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `C4`, `SIM`. Line length 100, target Python 3.11.

### Mypy — type checking

```bash
uv run mypy src/zerodict
```

Strict optional, warn on return-any, warn on unreachable code. The package is PEP 561 compliant (ships `py.typed`).

### Bandit — security linting

```bash
uv run bandit -r src/zerodict
```

Scans the runtime source for common Python security smells. The `tests/` and `examples/` directories are excluded.

### Vulture — dead code detection

```bash
uv run vulture src/zerodict --min-confidence 80
```

Flags unused functions, classes, and variables at confidence ≥ 80%.

### Run everything at once

```bash
uv run ruff check src/ && \
uv run ruff format --check src/ && \
uv run mypy src/zerodict && \
uv run bandit -r src/zerodict && \
uv run vulture src/zerodict --min-confidence 80 && \
uv run pytest
```

---

## Pre-commit Hooks

Pre-commit runs the quality pipeline locally before each commit and validates the commit message format.

### Troubleshooting

If committing from an IDE (PyCharm, VS Code, etc.) fails with `pre-commit not found`, the git hooks cannot locate the `pre-commit` executable. This typically happens because the IDE calls `git` outside the project virtualenv.

**Fix 1 — reinstall hooks** (most common cause after cloning or moving the repo):

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

**Fix 2 — install pre-commit globally** so any IDE can find it:

```bash
pipx install pre-commit
# or
uv tool install pre-commit
```

**Fix 3 — commit from terminal** with the venv active:

```bash
source .venv/bin/activate
git commit -m "feat: my change"
```

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Commit messages are validated automatically by a git hook and in CI.

```
feat: add flatten() method            # new feature (minor version bump)
fix: handle None in strict mode       # bug fix (patch version bump)
docs: update README examples          # documentation only
refactor: split helpers into modules  # code restructuring
test: add edge cases for set_many     # tests only
chore: rename dev scripts             # maintenance
```

Commit-msg validation is enforced both locally (pre-commit `commit-msg` hook) and in CI on PRs.

---

## Running Examples

```bash
uv run python examples/01_quickstart.py
```

The quickstart example covers the core usage scenarios: dot notation reading, Path API, array support, atomic batch updates, diff/change tracking, JSON serialization, dict interface, strict mode, and real-world patterns.

---

## Release Process

Versioning, changelog, and PyPI publication are split across two GitHub Actions workflows.

### 1. release-please (automatic, runs on `main`)

`.github/workflows/release.yml` runs the `googleapis/release-please-action` on every push to `main`. release-please reads the Conventional Commits accumulated since the last release and:

- Opens (or updates) a single open **release PR** that bumps `__version__` in `src/zerodict/__init__.py`, updates `CHANGELOG.md`, and updates `.release-please-manifest.json`.
- When that release PR is merged, release-please creates a git tag (`vX.Y.Z`) and a GitHub release.

To force a specific version (e.g. patch instead of the auto-detected minor), add a `Release-As: X.Y.Z` trailer to a commit message. Configuration lives in `release-please-config.json`.

### 2. publish.yml (manual, `workflow_dispatch`)

`.github/workflows/publish.yml` is a manual workflow. After release-please has created the GitHub release, dispatch the workflow from the Actions tab:

- The `build` job runs `uv build` to produce sdist and wheel.
- The `publish` job downloads the artifacts and uploads them to PyPI via `pypa/gh-action-pypi-publish@release/v1` using Trusted Publishing (OIDC, no API token).
- The `publish` job runs in the `pypi` GitHub environment, which is protected by environment rules (see repository Settings → Environments).

No `~/.pypirc` is used. No PyPI tokens are stored locally or in repo secrets.

### Day-to-day contributor flow

For everyday work you do not interact with the release flow at all — it runs from your Conventional Commits on `main`:

```
feat: add X         -> minor bump in next release PR
fix: handle Y       -> patch bump in next release PR
docs: update Z      -> no version bump
```

Manual `__version__` bumps and manual `CHANGELOG.md` edits are not needed and will be overwritten by release-please.

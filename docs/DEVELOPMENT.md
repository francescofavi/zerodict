# Development

## Purpose

Setup instructions for contributors: installing the project locally, running the quality pipeline, running tests, and running examples.

## Scope

Covers local development workflow only. Does not cover CI/CD or publishing — release is automated via Trusted Publishing on GitHub Actions and triggered manually from the Releases page.

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
uv run python examples/demo.py
```

The demo covers the core usage scenarios: dot notation reading, Path API, array support, atomic batch updates, diff/change tracking, JSON serialization, dict interface, strict mode, and real-world patterns.

---

## Release Process

Releases are cut via Trusted Publishing (OIDC) on GitHub Actions:

1. Bump the version in `src/zerodict/__init__.py` (`__version__`).
2. Update `CHANGELOG.md` with a new entry for the version.
3. Tag the commit (`git tag vX.Y.Z`) and push the tag.
4. The Release workflow (`.github/workflows/`) builds the sdist + wheel via `uv build` and publishes to PyPI through Trusted Publishing.

No `~/.pypirc` is used. No PyPI tokens are stored locally. Publishing is gated by GitHub environment protection rules — see the repository Settings → Environments page.

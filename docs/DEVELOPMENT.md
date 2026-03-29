# Development

## Purpose

Setup instructions for contributors: installing the project locally, running tests, and running examples.

## Scope

Covers local development workflow only. Does not cover CI/CD, publishing, or release management.

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

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

## Installation

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

With coverage:

```bash
uv run pytest --cov
```

Verbose output:

```bash
uv run pytest -v
```

---

## Running Examples

```bash
uv run python examples/demo.py
```

The demo covers 10 usage scenarios: dot notation, path API, arrays, batch updates, diff, JSON serialization, dict interface, strict mode, and real-world patterns.

---

## Pre-commit Hooks

This project uses pre-commit hooks for linting, formatting, and commit message validation.

### Troubleshooting

If committing from an IDE (PyCharm, VS Code, etc.) fails with `pre-commit not found`, the git hooks cannot locate the `pre-commit` executable. This typically happens because the IDE calls `git` outside the project virtualenv.

**Fix 1 - Reinstall hooks** (most common cause after cloning or moving the repo):

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

**Fix 2 - Install pre-commit globally** so any IDE can find it:

```bash
pipx install pre-commit
# or
uv tool install pre-commit
```

**Fix 3 - Commit from terminal** with the venv active:

```bash
source .venv/bin/activate
git commit -m "feat: my change"
```

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Commit messages are validated automatically by a git hook and in CI.

```
feat: add flatten() method          # new feature (minor version bump)
fix: handle None in strict mode     # bug fix (patch version bump)
docs: update README examples        # documentation only
refactor: split helpers into modules # code restructuring
test: add edge cases for set_many   # tests only
chore: rename dev scripts           # maintenance
```

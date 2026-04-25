# SNAPSHOT

## Purpose

Point-in-time snapshot of the project state at the moment this documentation cycle was generated. Used by the maintainer to compare drift between releases.

## Scope

- **Included:** version, supported runtimes, module/file metrics, test coverage, dependency lists, public API inventory, tooling configuration, release infrastructure status, current branch state.
- **Excluded:** historical changes (see `CHANGELOG.md` and `git log`), forward-looking plans, business analysis (see `FUNCTIONAL_ANALYSIS.md`).

This file is regenerated on each documentation cycle. The data it contains was current as of the last regeneration only.

---

## Release identity

| Field | Value |
|---|---|
| Package name | `zerodict` |
| Distribution name on PyPI | `zerodict` |
| Version (from `src/zerodict/__init__.py`) | `0.1.2` |
| Latest CHANGELOG entry | `0.1.1` (2026-03-30) |
| Version / CHANGELOG drift | **Yes** — `__version__ = "0.1.2"` has no matching CHANGELOG entry |
| Python support | `>=3.11` (3.11, 3.12, 3.13 declared in classifiers) |
| License | MIT |
| Build backend | hatchling |
| Build version source | `src/zerodict/__init__.py` (dynamic via `[tool.hatch.version]`) |

---

## Source metrics

| Module | LOC |
|---|---:|
| `src/zerodict/__init__.py` | 21 |
| `src/zerodict/diff_engine.py` | 249 |
| `src/zerodict/missing_path.py` | 73 |
| `src/zerodict/path_api.py` | 415 |
| `src/zerodict/serializer.py` | 69 |
| `src/zerodict/validator.py` | 182 |
| `src/zerodict/zerodict.py` | 274 |
| **Total** | **1,283** |

| Tests | LOC |
|---|---:|
| `tests/test_zerodict.py` | 837 |
| Test count | 92 (all passing) |
| Coverage (line) | 77% |

| Examples | LOC |
|---|---:|
| `examples/demo.py` | 253 |

---

## Public API inventory

The package's `__all__` is exactly:

```python
__all__ = ["ZeroDict", "MissingPath"]
```

### `ZeroDict` (public methods)

Constructor and core:
- `__init__(data=None)`
- `__getattr__`, `__setattr__`
- `__getitem__`, `__setitem__`, `__delitem__`
- `__len__`, `__contains__`, `__iter__`, `__eq__`, `__repr__`

Path API (delegated to `PathAPI`):
- `get_path(path, default=None, *, strict=False)`
- `set_path(path, value, *, strict=False)`
- `delete_path(path, *, strict=False)`
- `set_many(updates, *, strict=False)`
- `move(source_path, dest_path, *, strict=False)`

Serialization (delegated to `Serializer`):
- `to_dict()`
- `to_json(**kwargs)`
- `from_dict(d)` (static)
- `from_json(s)` (static)

Diff (delegated to `DiffEngine`):
- `diff(other)`

Dict interface:
- `keys()`, `values()`, `items()`
- `get(key, default=None)`
- `pop(key, *args)`
- `update(other)`
- `clear()`
- `setdefault(key, default=None)`
- `contains_key(key)`

Utility:
- `copy(deep=True)`

### `MissingPath` (public surface)

- `__init__(path)`
- `__bool__`, `__eq__`, `__hash__`, `__repr__`, `__str__`
- `__getattr__` (chains, warns past `MAX_MISSING_PATH_DEPTH`)
- `__setattr__` (always raises `AttributeError`)
- `__reduce__` (pickles to `None`)

Slots: `("_path",)`.

---

## Dependencies

### Runtime

```
[]
```

Zero runtime dependencies. Standard library only.

### Development

From `[dependency-groups].dev`:

| Package | Version pin |
|---|---|
| pytest | `>=8.3.5` |
| pytest-cov | `>=6.1.1` |
| pytest-mock | `>=3.14.0` |
| ruff | `>=0.11.8` |
| mypy | `>=1.15.0` |
| bandit | `>=1.7.10` |
| vulture | `>=2.13` |
| pre-commit | `>=4.2.0` |

---

## Tooling configuration summary

| Tool | Status | Notable settings |
|---|---|---|
| ruff (lint) | clean | rule set `E,F,W,I,N,UP,B,C4,SIM`; `E501` ignored; line length 100; target `py311` |
| ruff (format) | clean | applied across `src/` |
| mypy | clean | `strict_optional=True`; `warn_unreachable=True`; runs on `src/zerodict` |
| bandit | clean | exclude `tests`, `examples`; skips `B101,B403,B110` |
| vulture | clean | min confidence 80; runs on `src/` |
| pytest | 92 passing, 0 warnings | `addopts = -v`; testpaths `["tests"]` |
| coverage | 77% line | `pytest-cov` configured but no fail-under threshold |

---

## Documentation inventory

### Public (`docs/`)

| File | Purpose |
|---|---|
| `README.md` (repo root) | User-facing intro, installation, quick start, comparison table, known limits, anti-patterns, doc map |
| `docs/API_REFERENCE.md` | Comprehensive technical reference for every public symbol |
| `docs/ARCHITECTURE.md` | Module map, responsibilities, data flow |
| `docs/ANTI_PATTERNS.md` | User-facing guide to misuse patterns |
| `docs/DEVELOPMENT.md` | Contributor setup, quality pipeline, commit conventions, release process |
| `LICENSE` | MIT license |
| `SECURITY.md` | Security policy |
| `CHANGELOG.md` | Release log (release-please managed) |

`docs/USER_GUIDE.md` is intentionally not produced — the README is sufficient for a single-class library of this size.

### Internal (`.internal_docs/`)

| File | Purpose |
|---|---|
| `.internal_docs/SNAPSHOT.md` | This file |
| `.internal_docs/FUNCTIONAL_ANALYSIS.md` | Business / PM view |
| `.internal_docs/QUICKDOC.md` | Maintainer cheat sheet |
| `.internal_docs/LIMITATIONS.md` | Full limit analysis |
| `.internal_docs/ALTERNATIVES.md` | Library landscape comparison |
| `.internal_docs/BUG_REPORT.md` | Issues identified during the audit |
| `.internal_docs/QUALITY_REPORT.md` | Quality pipeline status |

---

## Release infrastructure

| Component | Status |
|---|---|
| `.github/workflows/ci.yml` | Present — runs lint/type/test on PRs |
| `.github/workflows/publish.yml` | Present — Trusted Publishing to PyPI on tag (manual approval via environment) |
| `.github/workflows/release.yml` | Present — release-please for changelog/version bumps |
| `release-please-config.json` | Present |
| `.release-please-manifest.json` | Present |
| `.pre-commit-config.yaml` | Present (ruff, mypy, bandit, vulture, conventional-pre-commit) |
| Trusted Publishing (OIDC) | Configured (no `~/.pypirc`, no API tokens) |

---

## Repository configuration

| Field | Value |
|---|---|
| `pyproject.toml` sdist exclude | excludes `.idea`, `dist`, dev scripts, `.pre-commit-config.yaml`, `.python-version`. **Does not exclude `.internal_docs/`** — see BUG_REPORT |
| `.gitignore` hidden-folder rule | `.*/` ignores all hidden directories; only `.github/` is whitelisted. **`.internal_docs/` is therefore not tracked by git** — see BUG_REPORT |
| `py.typed` marker | Present (`src/zerodict/py.typed`) — package is PEP 561 typed |
| `LICENSE` at root | Present (MIT) |
| `logo.png` at root | Present, referenced from README via raw GitHub URL |

---

## Known drift at snapshot time

1. `__version__` (`0.1.2`) ahead of latest `CHANGELOG.md` entry (`0.1.1`). A `0.1.2` entry must be added to `CHANGELOG.md` before tagging.
2. `.internal_docs/` is not yet tracked by git nor excluded from sdist.

Both items are listed as actionable in `BUG_REPORT.md`.

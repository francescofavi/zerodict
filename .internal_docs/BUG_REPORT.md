# BUG REPORT

## Purpose

Running list of issues identified during the documentation cycle audit. Includes correctness bugs, doc/code drift, packaging gaps, and candidate enhancements.

## Scope

- **Included:** every concrete issue derivable from the current code, configuration, or doc set, with severity, source location, and proposed direction.
- **Excluded:** speculative concerns without evidence, generic Python advice.

If no bugs are detected in a category, that is stated explicitly.

---

## Severity legend

| Level | Meaning |
|---|---|
| HIGH | Blocks release, breaks documented behavior, or actively misleads users. |
| MEDIUM | Drift between code and docs, packaging gap, low-impact correctness issue. |
| LOW | Polish, style, candidate enhancement. |

---

## HIGH

### H1 — Version / CHANGELOG drift

- **Where:** `src/zerodict/__init__.py` declares `__version__ = "0.1.2"`. `CHANGELOG.md` last entry is `0.1.1` (2026-03-30).
- **Symptom:** A `0.1.2` release cannot be cut cleanly via Trusted Publishing without a changelog entry, and `pre-release-review` (Stage 4) will flag this as a blocker.
- **Root cause:** Changelog generation lagged behind the version bump.
- **Fix direction:** Add a `0.1.2` entry to `CHANGELOG.md` summarizing the docs polish + SECURITY.md commit (a596b6c) and any other changes since `0.1.1`. Or, if `0.1.2` was a no-op bump, decide whether to ship it as a docs-only release or revert the bump.

### (none other identified)

---

## MEDIUM

### M1 — `.internal_docs/` is not tracked by git

- **Where:** `.gitignore` line 13: `.*/` (ignores all hidden directories) followed by line 16: `!.github/` (whitelists only `.github/`).
- **Symptom:** Internal docs cannot be versioned with the project. The skill that produced them expects them to be tracked.
- **Fix direction:** Add a whitelist entry `!.internal_docs/` to `.gitignore`. After that, `git add .internal_docs/*.md` will work and the directory ships under git.

### M2 — `.internal_docs/` is not excluded from sdist

- **Where:** `pyproject.toml` `[tool.hatch.build.targets.sdist].exclude` does not list `.internal_docs/`.
- **Symptom:** Once `.internal_docs/` is tracked by git (see M1), it would be packaged into the sdist on the next release, leaking maintainer-only content to PyPI consumers.
- **Fix direction:** Append `"/.internal_docs/**"` to the sdist `exclude` list. Verify with `uv build && tar -tzf dist/*.tar.gz | grep internal_docs` (should produce no output).

### M3 — `docs/API_REFERENCE.md` example for `move` on array elements was incorrect

- **Where:** `docs/API_REFERENCE.md`, "Move array elements" example.
- **Symptom:** The example claimed `inbox[0]` becomes `None` after `move("inbox[0]", "archive[0]")`. The actual code path uses `PathAPI.delete`, which calls `cur.pop(idx)` on lists — the element is removed and indices shift, so `inbox` becomes `[]`.
- **Status:** Fixed in this documentation cycle (correction applied to `docs/API_REFERENCE.md`).
- **Lesson:** Examples that depend on `delete_path` / `move` behavior on arrays must be cross-checked against `path_api.py:307`.

### M4 — Pre-existing `.internal_docs/FUNCTIONAL_ANALYSIS.md` referenced inexistent modules

- **Where:** Old `.internal_docs/FUNCTIONAL_ANALYSIS.md` (last touched 2026-02-18) referenced `token.py`, `constants.py`, `_validate_key`, `_estimate_size`, `_contains_object_id`. Current source has none of those — `Token` lives in `path_api.py`, all constants live in `validator.py`, and the validator helpers were renamed (`Validator.validate_key`, `Validator.estimate_size`, `Validator.contains_circular_ref`).
- **Symptom:** A maintainer reading the stale FUNCTIONAL_ANALYSIS would chase ghost files.
- **Status:** Fixed — file fully regenerated in this documentation cycle.

### M5 — Pre-existing `.internal_docs/QUICKDOC.md` referenced inexistent symbols

- **Where:** Old QUICKDOC referenced `constants.py`, `Token` in `token.py`, and `PathAPI._is_token_prefix()`.
- **Status:** Fixed — file fully regenerated.

---

## LOW

### L1 — Test coverage gap on rollback edge cases

- **Where:** `path_api.py:344-367` — `set_many` rollback. Coverage report shows `path_api.py` at 80% line coverage; the rollback branch is partly exercised but the "rollback itself fails" `RuntimeWarning` path lacks a dedicated test.
- **Symptom:** A regression in rollback warning behavior would pass CI silently.
- **Fix direction:** Add a parameterized test that injects a failing `PathAPI.set` during the rollback phase (e.g. via a mock that succeeds on the forward pass and raises on the backward pass) and asserts the `RuntimeWarning` is emitted.

### L2 — `validator.py` coverage at 54%

- **Where:** `validator.py` reports 54% line coverage. `Validator.contains_circular_ref` is among the under-tested helpers.
- **Symptom:** Refactoring the validator could regress untested branches.
- **Fix direction:** Either delete `contains_circular_ref` if it is genuinely unused at the public surface (a vulture run still flags nothing — it may be reachable via `_visited` tracking I'm missing) or write coverage tests.

### L3 — `diff_engine.py` coverage at 70%

- **Where:** `_walk_diff` and `_compare_lists` have less-exercised branches around mixed `dict` ↔ `ZeroDict` element comparison.
- **Fix direction:** Add tests that mix plain `dict` and `ZeroDict` inside lists, including circular cases.

### L4 — `MissingPath.__hash__` collision is documented in code but not in user docs

- **Where:** `missing_path.py:65-70` — clear maintainer-facing comment about the hash/eq contract. Not surfaced in user docs.
- **Fix direction:** Add a one-liner under `MissingPath` in `API_REFERENCE.md` noting that all instances hash the same as `None`. Already present in QUICKDOC and LIMITATIONS for maintainers.

### L5 — Candidate enhancement: `paths()` iterator

- **Where:** Not implemented.
- **Symptom:** Users who want to iterate every leaf path (e.g. for validation, serialization, debugging) must walk the structure manually.
- **Direction:** Add `ZeroDict.paths(*, include_arrays: bool = True) -> Iterator[str]` yielding tokenized paths in document order.

### L6 — Candidate enhancement: configurable security limits

- **Where:** `validator.py` constants are module-level, not exposed.
- **Symptom:** Legitimate large-data use cases must fork or monkey-patch.
- **Direction:** Introduce a `ZeroDictConfig` dataclass passed at construction; defaults preserve current behavior. Significant API surface increase — defer until there's user demand.

### L7 — `__repr__` truncation could mask key counts

- **Where:** `zerodict.py:266-272`. Truncates `repr(self._data)` at 500 chars and shows `~N of M keys`.
- **Symptom:** The "approximate" count is computed by counting `':` substrings in the truncated prefix, which can over- or under-count depending on values containing the literal `':`. Not a correctness bug, but a debug-friendliness gap.
- **Direction:** Compute the exact key count on the truncated dict by `len(self) - len(remaining)` if needed, or drop the approximation in favor of `f"{N} keys total, showing first 500 chars"`.

---

## Categories with no findings

- **Memory leaks:** none identified. All visited-set tracking is in `try/finally` blocks with `discard`.
- **Security:** bandit clean at zero findings (low/medium/high).
- **Dead code:** vulture clean at confidence ≥ 80.
- **Type errors:** mypy clean across `src/zerodict`.
- **Style violations:** ruff clean.

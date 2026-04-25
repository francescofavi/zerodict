# LIMITATIONS

## Purpose

Comprehensive analysis of every limit that ZeroDict imposes on its users — global caps and per-component caps. The README's "Known limits and open issues" section is a top-7 summary; this is the full table.

## Scope

- **Included:** every numeric or behavioral limit derivable from the source code, with its location, the consequence when hit, and the rationale where one is stated or clearly inferable.
- **Excluded:** speculative future limits, library-versus-alternative comparisons (see `ALTERNATIVES.md`).

---

## Global limits

All numeric limits are module-level constants in `src/zerodict/validator.py`. They are not user-configurable.

| Constant | Value | Source | Consequence on breach |
|---|---:|---|---|
| `MAX_NESTING_DEPTH` | 100 | `validator.py:17` | `ValueError` from `validate_path_depth`, `ZeroDict.__init__`, `Serializer.to_dict`, `DiffEngine._walk_diff`, `DiffEngine.compare`, `DiffEngine._compare_lists`. Message includes the offending depth and the path prefix. |
| `MAX_KEY_LENGTH` | 1000 (bytes / chars in ASCII) | `validator.py:18` | `ValueError` from `Validator.validate_key`. Message shows the first 50 chars of the offending key. |
| `MAX_VALUE_SIZE` | 10,000,000 (10 MB, `sys.getsizeof`-estimated) | `validator.py:19` | `ValueError` from `Validator.validate_value_size`. Message shows the estimated and max size. |
| `MAX_PATH_LENGTH` | 10,000 (chars) | `validator.py:20` | `ValueError` from `PathAPI.tokenize`. Message shows the first 100 chars of the offending path. |
| `MAX_ARRAY_INDEX` | 10,000 | `validator.py:16` | `IndexError` from `PathAPI.tokenize` (when the path requests a higher index) or `PathAPI.set` (when extension would exceed it). |
| `MAX_MISSING_PATH_DEPTH` | 100 | `validator.py:21` | `RuntimeWarning` (not an error) from `MissingPath.__getattr__`. The chain still extends — the warning exists to surface infinite-attribute-chain bugs. |
| `VALID_KEY_PATTERN` | `^[a-zA-Z0-9_-]+$` | `validator.py:23` | `ValueError` from `Validator.validate_key`. Non-ASCII gets a more specific error than other invalid characters. |

### Hard, behavioral limits (no constant)

| Limit | Source | Consequence |
|---|---|---|
| Keys must be `str` | `ZeroDict.__init__` | `TypeError` listing up to three offending keys. |
| Top-level value must be `dict` (or `None`) | `ZeroDict.__init__` | `TypeError` showing the actual type. |
| Negative array indices forbidden | `PathAPI.tokenize`, `PathAPI.set` | `ValueError` / `IndexError`. |
| Path syntax | `PathAPI.tokenize` | `ValueError` for empty path, leading `.`, trailing `.`, `..`, missing `]`, empty `[]`, non-numeric `[...]`. |
| Move source/dest constraints | `PathAPI.move` | `ValueError` for empty/whitespace paths, `source == dest`, dest as a syntactic descendant of source. |

---

## Per-component limits

### `ZeroDict` (constructor, write surface)

- **Construction must use `dict`.** Passing any other type raises `TypeError`. Passing `None` is allowed and yields an empty instance.
- **Underscore keys trigger a `UserWarning`.** A key starting with `_` collides with the `_data` attribute slot used internally; the constructor still accepts the key but warns the user to access it via bracket notation.
- **Circular references in input are rejected.** Detection is by `id()` tracking — same object encountered twice in the same wrap chain raises `ValueError`. Detection runs both for circular `dict` and for circular `list`.
- **Recursive size estimation can hit Python's recursion limit.** Beyond that, `Validator.estimate_size` converts the `RecursionError` into a more helpful `ValueError` referencing `MAX_NESTING_DEPTH`. Source: `validator.py:112`.
- **`__repr__` truncates at 500 chars.** The truncation is purely cosmetic; the data is intact. Sources of confusion would be debug output, where users may think keys are missing.
- **`copy(deep=True)` requires the data to be deepcopyable.** Non-deepcopyable values (e.g. open file handles) raise `TypeError` with a message pointing at `copy(deep=False)`.

### `PathAPI` (path operations)

- **Path grammar covers `.` and `[i]` only.** No wildcards, no slicing, no predicates, no JSONPath operators.
- **Array indices are non-negative only.** No negative indexing.
- **Array auto-extension on write fills with `None`.** Setting `arr[5]` on an empty array creates `[None, None, None, None, None, value]`. The user must keep this in mind when iterating, since type-uniform arrays are not enforced.
- **Setting a deeper path through an existing scalar overwrites it with a `UserWarning`.** Specifically: writing `a.b.c` when `a` is a string overwrites `a` with a `ZeroDict`. The lost value is shown in the warning message — but it *is* lost.
- **`set_many` is "all-or-nothing", but rollback can degrade.** When `deepcopy` of an original value fails, `set_many` keeps a reference to the live original instead. If that object is mutated after rollback, the rollback's "before state" is no longer the actual original. The library warns via `RuntimeWarning` only when the rollback step itself raises.
- **`move` cannot relocate into a child of the source.** Detected via prefix check (`dest.startswith(source + ".")` or `+ "["`) — the check is syntactic, so a non-overlapping logical ancestry that happens to share a prefix is not flagged. In practice this is correct because key/index syntax disambiguates.

### `DiffEngine` (comparison)

- **Diff path strings combine keys and indices without a separator.** `users[0].name` is the canonical form; `users.[0].name` would be wrong.
- **Equality with `ZeroDict` on the RHS raises on circular references.** Comparison via `to_dict()` is attempted; on `ValueError` the result is `False` rather than propagated.
- **Equality with a plain `dict` on the RHS uses `to_dict()` round-trip.** A circular reference inside the `ZeroDict` results in `False` (not a raised exception), because the `ValueError` is caught.
- **List comparison rejects mixed types element-by-element.** A `ZeroDict` element compared against a `dict` element is unwrapped on either side for the comparison, but a `list` element compared against a `ZeroDict` element returns `False`.
- **Comparison failures at leaf level are caught and warned.** If `a == b` raises (e.g. NumPy array semantics), `DiffEngine` records a `replace` and emits a `RuntimeWarning`.

### `Serializer` (conversion)

- **`to_json` requires every leaf to be JSON-serializable.** Otherwise `json.dumps` raises `TypeError` — uncaught.
- **`to_json` defaults differ from stdlib defaults.** `indent=2` and `ensure_ascii=False` are applied unless the user overrides via `**kwargs`.
- **`from_json` round-trip flattens `MissingPath` to `None`.** This is intentional (`__reduce__` returns `(None, ())`), but a `MissingPath` deliberately stored in the structure becomes `None` after the round-trip.

### `Validator` (security)

- **`estimate_size` is approximate.** It uses `sys.getsizeof` per element, which does not account for Python object overhead consistently across types and platforms. The 10 MB cap is therefore an order-of-magnitude limit, not a precise byte budget.
- **Key validation is ASCII-only.** Non-ASCII letters (accented characters, ideographs, emoji) are rejected with a specific error. This is a deliberate choice — non-ASCII keys would conflict with the path API grammar in subtle ways.

### `MissingPath` (sentinel)

- **Hash collides with `None`.** All `MissingPath` instances hash to `hash(None)` to preserve the eq/hash contract. In a `set` or `dict` keyed by missing-path-or-None, collisions are common but `__eq__` distinguishes them.
- **Chain depth warning, not error.** Past `MAX_MISSING_PATH_DEPTH`, attribute access still returns a deeper `MissingPath`; the warning exists to surface infinite-loop bugs in user code, not to bound the library.
- **Pickle round-trip loses identity.** `pickle.dumps(MissingPath("x"))` followed by `pickle.loads(...)` yields `None`, not a `MissingPath`. Code that pickles structures containing `MissingPath` should be aware.

---

## Behavioral choices that are limitations in disguise

These are not numeric caps, but they constrain how the library is used.

| Choice | Why it limits | Alternative would have been |
|---|---|---|
| Not thread-safe | Concurrent writers must coordinate externally | Internal `RLock` — rejected as incompatible with the zero-overhead read promise. |
| Limits not configurable | Cannot tune for legitimate large-data cases | A `ZeroDictConfig` dataclass; not implemented to keep the public surface minimal. |
| ASCII-only keys | International data must be transliterated or rebracketed | Allow Unicode in keys with a different reserved-character set; rejected to avoid path-grammar ambiguity. |
| Strict mode is per-call, not per-instance | Application must remember to pass `strict=True` everywhere it wants schema enforcement | Instance-level strict mode; rejected because a single instance is often used in mixed permissive/strict contexts. |
| `delete_path` on arrays pops (shifts indices) | Iteration patterns relying on stable indices break | Replace with `None` instead; rejected because dense arrays should remain dense. |
| `set_many` deepcopy with fallback | Rollback may not restore mutated-then-rolled-back objects exactly | Force deepcopy and raise on failure; rejected because some legitimate values (lambdas, sockets) cannot be deepcopied. |
| No `paths()` iterator | Users must manually walk to enumerate all leaves | Provide a `paths(include_arrays=True)` helper; tracked as a candidate enhancement (`BUG_REPORT.md`). |

# QUICKDOC

## Purpose

Maintainer cheat sheet. Short-form lookup. Not for users.

## Scope

One-liners for every public symbol, common task recipes, pitfalls the maintainer should remember, pointers to deeper internal docs.

---

## Public symbols (one-liner each)

### `ZeroDict`

| Symbol | Behavior |
|---|---|
| `ZeroDict(data=None)` | Wraps a dict, validates keys, recursively wraps nested dicts as `ZeroDict`, lists as wrapped lists. |
| `__getattr__(key)` | Returns stored value if `key` exists, else `MissingPath(key)`. Underscore-prefixed keys go to `object.__getattribute__`. |
| `__setattr__(key, value)` | Validates key, wraps value. Underscore-prefixed keys go to `object.__setattr__`. |
| `__getitem__(key)` | Plain dict semantics — raises `KeyError` if missing. |
| `__setitem__(key, value)` | Validates key with underscore warning, wraps value. |
| `__delitem__(key)` | Plain dict semantics. |
| `__len__`, `__contains__`, `__iter__` | Top-level dict semantics. |
| `__eq__(other)` | Delegates to `DiffEngine.compare`; supports plain `dict` on the RHS. |
| `__repr__()` | Truncates at 500 chars; shows approx-key-count tail when truncated; handles `RecursionError`. |
| `get_path(path, default=None, *, strict=False)` | `PathAPI.get`. |
| `set_path(path, value, *, strict=False)` | `PathAPI.set`. |
| `delete_path(path, *, strict=False) -> bool` | `PathAPI.delete`. Returns whether something was removed (non-strict). |
| `set_many(updates, *, strict=False)` | `PathAPI.set_many`. Atomic with rollback. |
| `move(source_path, dest_path, *, strict=False)` | `PathAPI.move`. |
| `to_dict() -> dict[str, Any]` | `Serializer.to_dict`. |
| `to_json(**kwargs) -> str` | `Serializer.to_json`. Defaults `indent=2`, `ensure_ascii=False`; kwargs forwarded to `json.dumps`. |
| `from_dict(d) -> ZeroDict` (static) | Equivalent to `ZeroDict(d)`. |
| `from_json(s) -> ZeroDict` (static) | `Serializer.from_json`. |
| `diff(other) -> list[dict]` | `DiffEngine.diff`. |
| `keys() / values() / items()` | Standard dict views. |
| `get(key, default=None)` | Top-level only. |
| `pop(key, *args)` | Top-level only. |
| `update(other)` | Validates all keys before any mutation. |
| `clear()` | Empties `_data`. |
| `setdefault(key, default=None)` | Validates key with underscore warning. |
| `contains_key(key) -> bool` | Same as `key in zd` but explicit. |
| `copy(deep=True) -> ZeroDict` | Deep by default; falls back to shallow on demand; raises `TypeError` for non-deepcopyable values when `deep=True`. |

### `MissingPath`

| Symbol | Behavior |
|---|---|
| `MissingPath(path)` | Stores `_path` via `object.__setattr__`. Slotted. |
| `__bool__()` | `False`. |
| `__eq__(other)` | `True` for `None` or another `MissingPath` with the same path. |
| `__hash__()` | `hash(None)` — to keep the eq/hash contract with `None`. |
| `__getattr__(key)` | Returns a deeper `MissingPath`. Warns past `MAX_MISSING_PATH_DEPTH`. |
| `__setattr__(key, value)` | Always raises `AttributeError` — points the user at `set_path()`. |
| `__reduce__()` | Pickles to `None`. |
| `__repr__() / __str__()` | `"MissingPath('x.y')"` / `"None"`. |

---

## Internal classes (one-liner each)

| Symbol | Module | Role |
|---|---|---|
| `Token(key=None, idx=None)` | `path_api.py` | Path component dataclass; exactly one of key/idx must be set, validated in `__post_init__`. |
| `PathAPI.tokenize(path)` | `path_api.py` | Parses path string into `list[Token]`. Rejects empty paths, leading/trailing/consecutive dots, non-numeric indices, missing brackets. |
| `PathAPI.get(zd, path, default, *, strict)` | `path_api.py` | Walks tokens; key on non-dict / index on non-list / missing key / out-of-range index → `default` (non-strict) or raise (strict). |
| `PathAPI.set(zd, path, value, *, strict)` | `path_api.py` | Walks tokens, materializes intermediates by next-token type, warns on incompatible-type overwrites, extends arrays with `None` to reach high indices. |
| `PathAPI.delete(zd, path, *, strict) -> bool` | `path_api.py` | Returns whether something was deleted. Array deletion is `pop(idx)` — shifts subsequent indices. |
| `PathAPI.set_many(zd, updates, *, strict)` | `path_api.py` | Per-path backup (`deepcopy` with fallback) + per-path root-key existence; rolls back in order on failure; warns via `RuntimeWarning` if rollback itself fails. |
| `PathAPI.move(zd, source, dest, *, strict)` | `path_api.py` | Validates non-empty paths, source != dest, dest not a syntactic descendant of source. Uses `MissingPath` sentinel as "not found" marker. Set-then-delete with rollback. |
| `Validator.validate_key(key)` | `validator.py` | Empty / length / regex / non-ASCII / reserved-char checks. Raises `ValueError`. |
| `Validator.validate_dict_key(key, warn_underscore=False)` | `validator.py` | Type check + `validate_key` + optional underscore warning. |
| `Validator.validate_value_size(value)` | `validator.py` | Calls `estimate_size`; raises if over `MAX_VALUE_SIZE`. |
| `Validator.estimate_size(obj, visited)` | `validator.py` | Recursive `sys.getsizeof` sum with `id()` tracking. Raises `ValueError` on `RecursionError`. |
| `Validator.validate_path_depth(tokens, path)` | `validator.py` | Rejects token list longer than `MAX_NESTING_DEPTH`. |
| `Validator.get_max_depth(obj, visited)` | `validator.py` | Computes max nesting of `ZeroDict` / `dict` / `list` / `tuple` / `set`. |
| `Validator.contains_circular_ref(obj, target_id, visited)` | `validator.py` | True if `obj` graph reaches `target_id` (currently unused at the public surface, kept for completeness). |
| `Serializer.to_dict(zd, _visited, _depth)` | `serializer.py` | Recursive unwrap. Tracks ids and depth. |
| `Serializer.to_json(zd, **kwargs)` | `serializer.py` | `json.dumps(to_dict(zd), **{indent:2, ensure_ascii:False, **kwargs})`. |
| `Serializer.from_json(s)` | `serializer.py` | `ZeroDict(json.loads(s))`. |
| `DiffEngine.diff(zd1, zd2)` | `diff_engine.py` | Public diff. Initializes `visited: set[tuple[int, int]]` and walks. |
| `DiffEngine._walk_diff(...)` | `diff_engine.py` | Recursive engine. Plain dicts are wrapped on entry to keep granularity. |
| `DiffEngine.compare(zd1, other, _visited, _depth)` | `diff_engine.py` | Equality with plain dict + `ZeroDict` on the RHS. Tracks `(id, id)` pairs and depth. |
| `DiffEngine._compare_lists(list1, list2, _visited, _depth)` | `diff_engine.py` | Per-element comparison with mixed-type ZeroDict/dict handling and list-pair id tracking. |

---

## Common task recipes

| Task | Recipe |
|---|---|
| Add a new public method on `ZeroDict` | Add to `zerodict.py` as a thin wrapper that delegates to a static method on the appropriate helper class. Update `API_REFERENCE.md` and `QUICKDOC.md`. Add tests in `tests/test_zerodict.py`. |
| Add a new security limit | Add the constant in `validator.py`, import where needed, document in `API_REFERENCE.md` security table and `LIMITATIONS.md`. |
| Tighten / loosen an existing limit | Change the constant in `validator.py`. Update `API_REFERENCE.md`, `LIMITATIONS.md`, and any test that asserts the previous value. |
| Add a new path API operation | Implement as `@staticmethod` on `PathAPI`. Wire a thin wrapper on `ZeroDict`. Document. |
| Bump runtime Python | Update `requires-python` in `pyproject.toml`, `target-version` in ruff config, `python_version` in mypy config, classifiers, `DEVELOPMENT.md`, README badge. |
| Cut a release | Bump `__version__` in `src/zerodict/__init__.py`, add `CHANGELOG.md` entry, tag, push tag — Trusted Publishing handles the rest. |

---

## Pitfalls

- **`MissingPath` is not `None`.** `is None` is False, `== None` is True. Code that uses `is None` against ZeroDict reads will silently skip the missing branch.
- **Dot-notation writes are shallow only.** `zd.a = ...` works; `zd.a.b = ...` only works if `a` already exists. Otherwise it raises `AttributeError` from `MissingPath`. Use `set_path` for deep writes.
- **`delete_path` on an array element pops it.** Subsequent indices shift. Multiple deletes must be done from highest index to lowest.
- **`copy(deep=True)` raises on non-deepcopyable values.** Examples: open file handles, sockets, certain custom classes. The error message points at `copy(deep=False)`.
- **`set_many` rollback uses `deepcopy` with a fallback to the live reference.** For values where deepcopy fails, the rollback restores the same object — mutations to that object after rollback would still be visible.
- **`__setattr__` underscore guard relies on attribute names.** Adding internal attributes prefixed with `_` does NOT need a guard; adding non-underscore internal attributes WILL break, since it would route to `_data` instead of the instance `__dict__`. (See `_data` itself, set via `object.__setattr__`.)
- **`MissingPath.__hash__` returns `hash(None)` deliberately** to preserve the eq/hash contract. Two different `MissingPath`s hash equal — they are *not* distinguishable in a `set` until `__eq__` is checked.
- **`ZeroDict` is not thread-safe.** Concurrent writers share `_data` without a lock.

---

## Pointers to deeper internal docs

- Limit table and per-component impact → `LIMITATIONS.md`
- External alternatives we benchmark against → `ALTERNATIVES.md`
- Open issues found during the audit → `BUG_REPORT.md`
- Quality pipeline status → `QUALITY_REPORT.md`
- Point-in-time snapshot of versions, LOC, coverage → `SNAPSHOT.md`

# Architecture - ZeroDict

## Purpose

Describes the internal architecture of ZeroDict: components, responsibilities, boundaries, and data flow.

## Scope

- **Included:** Module structure, class responsibilities, delegation patterns, data flow during read/write/diff operations.
- **Excluded:** Public API details (see [API_REFERENCE.md](API_REFERENCE.md)), usage examples (see [README](../README.md)).

---

## Components

ZeroDict is organized into six modules under `src/zerodict/`:

| Module | Class | Responsibility |
|--------|-------|----------------|
| `zerodict.py` | `ZeroDict` | Public API surface, dot notation access, dict interface |
| `path_api.py` | `PathAPI`, `Token` | Path tokenization, navigation, deep get/set/delete, batch updates, move |
| `diff_engine.py` | `DiffEngine` | Structural diff and equality comparison between ZeroDict instances |
| `serializer.py` | `Serializer` | Conversion to/from plain dict and JSON |
| `validator.py` | `Validator` | Key/value/path validation, security constants, circular reference detection |
| `missing_path.py` | `MissingPath` | Sentinel object for non-existent paths |

### `__init__.py`

Exports only `ZeroDict` and `MissingPath`. All other classes are internal.

---

## Responsibilities

### ZeroDict (facade)

`ZeroDict` is the only user-facing class. It:

- Wraps a plain `dict[str, Any]` in `self._data`
- Provides dot notation via `__getattr__` / `__setattr__`
- Provides bracket notation via `__getitem__` / `__setitem__`
- Delegates all complex operations to specialized classes

`ZeroDict` does not contain business logic for path traversal, diffing, or serialization.

### PathAPI (path operations)

Handles all path-based operations:

- **Tokenization:** Parses path strings (`"a.b[0].c"`) into `Token` sequences (key or index)
- **Navigation:** Traverses nested ZeroDict/list structures following token sequences
- **Deep creation:** Creates intermediate dicts/lists when setting paths in non-strict mode
- **Batch updates:** `set_many` with selective backup and atomic rollback
- **Move:** Atomic source-to-destination relocation with circular reference checks

### DiffEngine (comparison)

- **diff:** Walks two ZeroDict trees in parallel, producing add/remove/replace operations
- **compare:** Deep equality check between ZeroDict and ZeroDict or plain dict
- Tracks visited pairs to detect circular references

### Serializer (conversion)

- **to_dict:** Recursively unwraps ZeroDict instances to plain dicts
- **to_json / from_json:** JSON round-trip via `json.dumps` / `json.loads`
- Tracks visited objects to detect circular references

### Validator (security)

- **Key validation:** Enforces `[a-zA-Z0-9_-]` pattern, length limits, ASCII-only
- **Value size:** Estimates object size recursively, rejects values exceeding 10MB
- **Path depth:** Enforces maximum 100 levels
- **Circular references:** Detection via object identity (`id()`) tracking
- Defines all security constants (`MAX_NESTING_DEPTH`, `MAX_KEY_LENGTH`, etc.)

### MissingPath (sentinel)

- Returned by `ZeroDict.__getattr__` when accessing non-existent keys
- Falsy, equals `None` via `__eq__`, hashable
- Supports chaining (`zd.a.b.c` returns `MissingPath("a.b.c")`) up to depth limit
- Raises `AttributeError` on assignment with a descriptive message
- Serializes to `None` via pickle

---

## Boundaries

```
User code
    |
    v
ZeroDict (public API)
    |
    +---> PathAPI      (path operations)
    +---> DiffEngine   (diff and equality)
    +---> Serializer   (dict/JSON conversion)
    |
    +---> Validator    (used by all modules)
    +---> MissingPath  (returned to user code)
```

- **User code** interacts only with `ZeroDict` and `MissingPath`.
- **ZeroDict** delegates to `PathAPI`, `DiffEngine`, and `Serializer` via static method calls.
- **Validator** is used by all modules but never exposed to user code.
- **PathAPI**, **DiffEngine**, and **Serializer** do not depend on each other.

---

## Data Flow

### Read (`zd.get_path("a.b[0].c")`)

1. `ZeroDict.get_path` delegates to `PathAPI.get`
2. `PathAPI.tokenize` parses the path into `[Token(key="a"), Token(key="b"), Token(idx=0), Token(key="c")]`
3. `Validator.validate_path_depth` checks depth limit
4. `PathAPI` navigates through `ZeroDict._data`, unwrapping nested ZeroDicts and indexing lists
5. Returns the value, or `default` if not found (or raises in strict mode)

### Write (`zd.set_path("a.b[0].c", value)`)

1. `ZeroDict.set_path` delegates to `PathAPI.set`
2. Path is tokenized and validated
3. `PathAPI` navigates/creates intermediate structures (dicts or lists)
4. `ZeroDict._wrap` converts dict/list values to ZeroDict/wrapped-list
5. `Validator.validate_value_size` checks value size
6. Value is assigned at the target location

### Batch Write (`zd.set_many(updates)`)

1. For each path in `updates`, backup the current value at the top-level key
2. Apply each `set_path` sequentially
3. On any error, restore all backed-up values (rollback)
4. Memory: O(update_size), not O(total_data_size)

### Diff (`zd1.diff(zd2)`)

1. `DiffEngine.diff` starts a recursive walk from both roots
2. At each level, compares keys (for dicts) or indices (for lists)
3. Produces `add`, `remove`, or `replace` entries with paths
4. Tracks visited pairs to prevent infinite loops on circular structures

### Construction (`ZeroDict(data)`)

1. Type-check: must be `dict` with string keys
2. `Validator.validate_key` on each key
3. `Validator.validate_value_size` on the entire input
4. `ZeroDict._wrap` recursively converts nested dicts to ZeroDicts and validates circular references via `id()` tracking

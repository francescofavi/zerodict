# Architecture

## Purpose

Describes the internal architecture of ZeroDict: components, responsibilities, boundaries, and data flow.

## Scope

- **Included:** module structure, class responsibilities, delegation patterns, data flow during read / write / diff / batch / move operations.
- **Excluded:** public API details (see [API_REFERENCE.md](API_REFERENCE.md)), usage examples (see [README](https://github.com/francescofavi/zerodict/blob/main/README.md)).

---

## Components

ZeroDict is organized into seven files under `src/zerodict/` (one of which is the package marker):

| Module | Class(es) | Responsibility |
|--------|-----------|----------------|
| `zerodict.py` | `ZeroDict` | Public API surface — dot notation, dict interface, delegation to specialized classes |
| `path_api.py` | `PathAPI`, `Token` | Path tokenization, navigation, deep get/set/delete, batch updates, move |
| `diff_engine.py` | `DiffEngine` | Structural diff and equality comparison between ZeroDict instances |
| `serializer.py` | `Serializer` | Conversion to/from plain `dict` and JSON |
| `validator.py` | `Validator` | Key/value/path validation, security constants, circular reference detection |
| `missing_path.py` | `MissingPath` | Sentinel object returned for non-existent paths |
| `__init__.py` | — | Re-exports `ZeroDict` and `MissingPath`; defines `__version__` |

The package's `__all__` is `["ZeroDict", "MissingPath"]`. Every other class (`PathAPI`, `Token`, `DiffEngine`, `Serializer`, `Validator`) is internal and not part of the public API.

### Security constants

All numeric limits live as module-level constants in `validator.py`:

| Constant | Value |
|----------|-------|
| `MAX_NESTING_DEPTH` | 100 |
| `MAX_KEY_LENGTH` | 1000 (bytes) |
| `MAX_VALUE_SIZE` | 10,000,000 (10 MB) |
| `MAX_ARRAY_INDEX` | 10,000 |
| `MAX_PATH_LENGTH` | 10,000 (chars) |
| `MAX_MISSING_PATH_DEPTH` | 100 |
| `VALID_KEY_PATTERN` | regex `^[a-zA-Z0-9_-]+$` |

These are imported by every module that needs them; there is no separate `constants.py` file.

---

## Responsibilities

### `ZeroDict` (facade)

`ZeroDict` is the only user-facing class besides `MissingPath`. It:

- Wraps a plain `dict[str, Any]` in `self._data`
- Provides dot notation via `__getattr__` / `__setattr__`
- Provides bracket notation via `__getitem__` / `__setitem__`
- Implements the standard dict interface (`__len__`, `__contains__`, `keys`, `values`, `items`, `get`, `pop`, `update`, `clear`, `setdefault`, iteration)
- Delegates path operations, diff, comparison, and serialization to specialized classes via static method calls

`ZeroDict` does not contain business logic for path traversal, diffing, or serialization.

### `PathAPI` (path operations)

Static-method-only class. Handles all path-based operations:

- **Tokenization:** parses path strings (`"a.b[0].c"`) into a `list[Token]` where each `Token` carries either a dict `key` or an array `idx` (never both).
- **Navigation:** traverses nested `ZeroDict` / `list` structures by walking the token sequence.
- **Deep creation:** when setting a path in non-strict mode, creates intermediate `ZeroDict` or `list` containers based on the next token's type.
- **Batch updates:** `set_many` records pre-write state per modified path and rolls back on failure.
- **Move:** atomic source-to-destination relocation with circular reference checks (`dest` cannot be a child of `source`).

### `DiffEngine` (comparison)

- **`diff`:** walks two `ZeroDict` trees in parallel, producing a flat list of `add`, `remove`, and `replace` operations annotated with their path.
- **`compare`:** deep equality check between a `ZeroDict` and either another `ZeroDict` or a plain `dict`.
- Both algorithms track visited `(id(a), id(b))` pairs and depth to defeat circular references and pathological nesting.

### `Serializer` (conversion)

- **`to_dict`:** recursively unwraps `ZeroDict` instances to plain `dict[str, Any]`.
- **`to_json` / `from_json`:** JSON round-trip via `json.dumps` / `json.loads`. `to_json` defaults to `indent=2` and `ensure_ascii=False`, but accepts arbitrary `**kwargs` forwarded to `json.dumps`.
- Tracks visited object IDs and depth.

### `Validator` (security)

- **Key validation:** enforces the `[a-zA-Z0-9_-]+` pattern, length cap, ASCII-only.
- **Value size:** estimates object size recursively via `sys.getsizeof`, rejects values exceeding `MAX_VALUE_SIZE`.
- **Path depth:** rejects token sequences longer than `MAX_NESTING_DEPTH`.
- **Circular reference detection:** tracks object identity via `id()` and a `visited: set[int]`.

### `MissingPath` (sentinel)

- Returned by `ZeroDict.__getattr__` when accessing a non-existent top-level key.
- Falsy in boolean context, equals `None` via `__eq__`, hashes to `hash(None)`.
- Supports chaining (`zd.a.b.c` returns `MissingPath("a.b.c")`) and warns when the chain exceeds `MAX_MISSING_PATH_DEPTH`.
- Raises `AttributeError` on assignment with a descriptive message that points the user at `set_path()`.
- Pickles to `None` via `__reduce__`.

---

## Boundaries

```
User code
    |
    v
ZeroDict (public API) ----+-----> MissingPath (returned to user code)
    |                     |
    +--> PathAPI          |       (sentinel for missing paths)
    +--> DiffEngine       |
    +--> Serializer       |
    |                     |
    +--> Validator <------+
         (used by all internal modules)
```

- **User code** interacts only with `ZeroDict` and `MissingPath`.
- **`ZeroDict`** delegates to `PathAPI`, `DiffEngine`, and `Serializer` via static method calls.
- **`Validator`** is shared by every internal module but never exposed to user code.
- `PathAPI`, `DiffEngine`, and `Serializer` do not depend on each other.
- `MissingPath` depends only on `Validator` (for `MAX_MISSING_PATH_DEPTH`).

---

## Data Flow

### Read — `zd.get_path("a.b[0].c")`

1. `ZeroDict.get_path` delegates to `PathAPI.get`.
2. `PathAPI.tokenize` parses the path into `[Token(key="a"), Token(key="b"), Token(idx=0), Token(key="c")]`.
3. `Validator.validate_path_depth` rejects token sequences longer than 100.
4. `PathAPI.get` walks the tokens, descending into nested `ZeroDict._data` for keys and into `list` for indices.
5. Returns the value, or `default` if missing (or raises in strict mode).

### Write — `zd.set_path("a.b[0].c", value)`

1. `ZeroDict.set_path` delegates to `PathAPI.set`.
2. Path is tokenized and depth-validated.
3. `PathAPI.set` walks the tokens. For each non-terminal token, if the next token is a key it ensures a `ZeroDict` is in place; if the next token is an index it ensures a `list` is in place. In non-strict mode, missing intermediates are created; existing values of incompatible type are overwritten with a `UserWarning`.
4. At the terminal token, `ZeroDict._wrap` converts dict/list values into `ZeroDict` / wrapped `list` and runs `Validator.validate_value_size`.
5. The value is assigned at the target location.

### Batch write — `zd.set_many(updates)`

1. For each `(path, new_value)` pair in `updates`:
   - The value currently at `path` is fetched in strict mode via `PathAPI.get`. If it exists, it is `deepcopy`-ed (with a fallback to the original reference for non-copyable objects) and recorded in `rollback_info`.
   - The root token's key and pre-write existence flag are also recorded so a newly-created root can be torn down on rollback.
   - `PathAPI.set` is invoked.
2. On any exception during the loop, `set_many` walks `rollback_info` in order and:
   - Restores the original value (`PathAPI.set` with `strict=False`) if the path existed before.
   - Otherwise deletes the path and, if the root key was created during this batch, deletes the root key as well.
   - Re-raises the original exception.
3. If a rollback step itself raises, the failure is collected and reported via `RuntimeWarning` so the user knows the structure may be in an inconsistent state.
4. Backup memory is `O(sum-of-sizes-of-touched-paths)`, not `O(total_data_size)`.

### Move — `zd.move(source, dest)`

1. Source and destination paths are validated. Move is rejected with `ValueError` when:
   - Either path is empty or whitespace-only.
   - Source equals destination.
   - Destination is a syntactic descendant of source (`dest.startswith(source + ".")` or `dest.startswith(source + "[")`).
2. `PathAPI.get` fetches the source value using a `MissingPath` sentinel as default to distinguish "stored `None`" from "not found".
3. In non-strict mode, a missing source is a no-op. In strict mode it raises `KeyError`. Strict mode also rejects an existing destination.
4. `PathAPI.set` writes the value at the destination, then `PathAPI.delete` removes the source.
5. On any error during the set/delete pair, the original state is restored (destination cleared or restored to its prior value, source re-set).

### Diff — `zd1.diff(zd2)`

1. `DiffEngine.diff` starts a recursive walk from both roots with a shared `visited: set[tuple[int, int]]` and `depth=0`.
2. At each node:
   - **Both `ZeroDict`:** compares key sets — keys only in `a` produce `remove`, keys only in `b` produce `add`, common keys recurse with the key appended to the current prefix.
   - **Both `list`:** compares element-by-element up to the shorter length, then emits `remove` / `add` for trailing elements.
   - **Otherwise:** compares values; if unequal (or the comparison itself raises), emits `replace` and warns on comparison failures.
3. Plain `dict` values encountered mid-walk are converted to `ZeroDict` for granular comparison.
4. Path strings are normalized so array indices follow keys without an intermediate dot (e.g. `users[0].name`, not `users.[0].name`).

### Construction — `ZeroDict(data)`

1. Type-check: `data` must be `dict` (or `None`).
2. All top-level keys must be `str`; non-string keys produce `TypeError` listing up to three offenders.
3. Every top-level key is run through `Validator.validate_key`.
4. Keys starting with `_` issue a `UserWarning` advising bracket-notation access (they would otherwise shadow internal attributes).
5. `Validator.validate_value_size` runs on the entire input.
6. Values are wrapped recursively via `ZeroDict._wrap`, which:
   - Returns existing `ZeroDict` instances unchanged after re-checking depth.
   - Recursively wraps nested `dict` into new `ZeroDict`, tracking `id()` to reject circular references.
   - Recursively wraps `list` elements with the same id-tracking.
   - Returns scalar values unchanged.

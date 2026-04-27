# API Reference - ZeroDict

## Purpose

Complete technical reference for all public APIs in the ZeroDict library, including signatures, parameters, return types, exceptions, side effects, and usage examples.

## Scope

- **Included:** All public classes (`ZeroDict`, `MissingPath`), all public methods, security constants, error handling patterns, performance considerations.
- **Excluded:** Internal/private methods (prefixed with `_`), implementation details of delegation classes (`PathAPI`, `DiffEngine`, `Serializer`, `Validator`).

For high-level usage and examples, see the [README](../README.md).

## Table of Contents

1. [Global Concepts](#global-concepts)
2. [Core ZeroDict Class](#core-zerodict-class)
3. [Path Operations](#path-operations)
4. [Batch Operations](#batch-operations)
5. [Comparison and Change Tracking](#comparison-and-change-tracking)
6. [Serialization](#serialization)
7. [Dictionary Interface Methods](#dictionary-interface-methods)
8. [Security and Validation](#security-and-validation)
9. [MissingPath Sentinel](#missingpath-sentinel)

---

## Global Concepts

### Path Notation

ZeroDict supports two types of path notation:

**Dot notation for nested dictionaries:**
```python
"user.profile.name"          # Accesses nested dict keys
"database.config.host"       # Multiple levels
```

**Array indices with brackets:**
```python
"items[0]"                   # First element of array
"items[0].name"              # Property of first element
"data.records[5].values[2]"  # Nested arrays
```

**Path rules:**
- Cannot start or end with a dot
- Cannot contain consecutive dots (`..`)
- Array indices must be non-negative integers
- Maximum path length: 10,000 characters
- Maximum depth: 100 levels

### Key Validation

Dictionary keys must follow strict rules for security:

**Allowed characters:**
- ASCII letters (a-z, A-Z)
- Numbers (0-9)
- Underscore (_)
- Hyphen (-)

**Not allowed:**
- Spaces
- Special characters (. [ ] are reserved for path API)
- Non-ASCII characters (emoji, accented letters)
- Empty strings

**Examples:**
```python
# Valid keys
"username"
"user_name"
"user-123"
"API_KEY"

# Invalid keys
"user.name"    # Contains reserved character '.'
"items[0]"     # Contains reserved characters '[]'
"my key"       # Contains space
"café"         # Contains non-ASCII character
""             # Empty string
```

### Security Limits

The following limits protect against DoS attacks:

| Limit | Value | Purpose |
|-------|-------|---------|
| `MAX_NESTING_DEPTH` | 100 | Prevents stack overflow from deeply nested structures |
| `MAX_KEY_LENGTH` | 1000 bytes | Prevents memory exhaustion from huge keys |
| `MAX_VALUE_SIZE` | 10MB | Prevents memory exhaustion from huge values |
| `MAX_ARRAY_INDEX` | 10,000 | Prevents memory exhaustion from sparse arrays |
| `MAX_PATH_LENGTH` | 10,000 chars | Prevents parsing overhead |
| `MAX_MISSING_PATH_DEPTH` | 100 | Prevents memory leaks from infinite attribute chains |

All limits are enforced consistently across all operations.

### Module Structure

ZeroDict is organized into the following modules:

| Module | Purpose |
|--------|---------|
| `zerodict.py` | Main `ZeroDict` class with public API |
| `path_api.py` | `PathAPI` class for path tokenization, navigation, and manipulation; `Token` dataclass |
| `diff_engine.py` | `DiffEngine` class for structural diff and equality comparison |
| `serializer.py` | `Serializer` class for dict/JSON conversion |
| `validator.py` | `Validator` class, security constants, and validation patterns |
| `missing_path.py` | `MissingPath` sentinel class for non-existent paths |

### Type System

ZeroDict uses modern Python 3.12+ type hints:

```python
from typing import Any

# Constructor
def __init__(self, data: dict[str, Any] | None = None) -> None: ...

# Path operations
def get_path(self, path: str, default: Any = None, *, strict: bool = False) -> Any: ...
def set_path(self, path: str, value: Any, *, strict: bool = False) -> None: ...

# Batch operations
def set_many(self, updates: dict[str, Any], *, strict: bool = False) -> None: ...

# Serialization
def to_dict(self) -> dict[str, Any]: ...
def to_json(self, **kwargs) -> str: ...
```

---

## Core ZeroDict Class

### `ZeroDict(data=None)`

Constructor that creates a new ZeroDict instance, optionally initializing it with data.

**Parameters:**
- `data` (dict[str, Any] | None): Initial dictionary data. All nested dicts are automatically wrapped into ZeroDict instances. Default: `None` (creates empty ZeroDict).

**Raises:**
- `TypeError`: If `data` is not a dict or contains non-string keys
- `ValueError`: If keys are invalid, exceed size limits, or circular references detected

**Side Effects:**
- Deep copies and wraps input data
- Validates all keys and values
- Checks for circular references
- Estimates data size to enforce limits

**Examples:**

**Basic initialization:**
```python
from zerodict import ZeroDict

# Empty ZeroDict
ed = ZeroDict()

# From plain dict
ed = ZeroDict({"name": "Alice", "age": 30})

# Nested structures auto-wrapped
ed = ZeroDict({
    "user": {
        "profile": {"name": "Alice"},
        "settings": {"theme": "dark"}
    }
})
# ed.user is a ZeroDict instance
# ed.user.profile is a ZeroDict instance
```

**With arrays:**
```python
ed = ZeroDict({
    "teams": [
        {"name": "Engineering", "size": 10},
        {"name": "Product", "size": 5}
    ]
})
# Arrays are preserved as lists
# Array elements that are dicts become ZeroDict instances
```

**Validation errors:**
```python
# Invalid key characters
try:
    ed = ZeroDict({"user.name": "value"})  # '.' is reserved
except ValueError as e:
    print(e)  # "Key 'user.name' contains invalid character(s): ['.']"

# Non-string keys
try:
    ed = ZeroDict({123: "value"})
except TypeError as e:
    print(e)  # "All dict keys must be strings"

# Circular reference protection
data = {}
data["self"] = data
try:
    ed = ZeroDict(data)
except ValueError as e:
    print(e)  # "Circular reference detected in input dict"
```

---

## Path Operations

### `get_path(path, default=None, *, strict=False)`

Navigate nested structures using path notation and retrieve values safely.

**Parameters:**
- `path` (str): Dot notation path (e.g., `"user.profile.name"` or `"items[0].id"`). Required.
- `default` (Any): Value to return if path not found (when `strict=False`). Default: `None`.
- `strict` (bool): If `True`, raise exceptions on missing paths or type mismatches. If `False`, return `default`. Default: `False`.

**Returns:**
- Value at the path, or `default` if not found (non-strict mode)

**Raises:**
- `ValueError`: If path is invalid, empty, or exceeds depth limit
- `KeyError`: If `strict=True` and key not found
- `TypeError`: If `strict=True` and cannot traverse (e.g., accessing dict key on non-dict)
- `IndexError`: If `strict=True` and array index out of range

**Examples:**

**Basic usage:**
```python
ed = ZeroDict({
    "user": {"profile": {"name": "Alice", "age": 30}},
    "settings": {"theme": "dark"}
})

# Simple path
name = ed.get_path("user.profile.name")  # "Alice"

# Missing path returns None (default)
email = ed.get_path("user.profile.email")  # None

# Custom default
port = ed.get_path("server.port", default=8000)  # 8000
```

**Array access:**
```python
ed = ZeroDict({
    "items": [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"}
    ]
})

# Array element
first_name = ed.get_path("items[0].name")  # "Item 1"

# Out of range returns default
tenth = ed.get_path("items[9].name", default="N/A")  # "N/A"
```

**Strict mode:**
```python
ed = ZeroDict({"data": {"value": 42}})

# Strict mode raises on missing paths
try:
    result = ed.get_path("data.missing", strict=True)
except KeyError as e:
    print("Key not found")

# Strict mode validates types
ed2 = ZeroDict({"user": None})
try:
    # Cannot traverse through None
    result = ed2.get_path("user.name", strict=True)
except TypeError as e:
    print("Cannot traverse None value")
```

---

### `set_path(path, value, *, strict=False)`

Set value at any path depth, automatically creating intermediate structures.

**Parameters:**
- `path` (str): Dot notation path. Required.
- `value` (Any): Value to set. Will be auto-wrapped if it's a dict or list. Required.
- `strict` (bool): If `True`, fail if intermediate paths don't exist. If `False`, create them automatically. Default: `False`.

**Returns:**
- None

**Raises:**
- `ValueError`: If path is invalid, empty, or exceeds depth limit
- `KeyError`: If `strict=True` and intermediate path doesn't exist
- `TypeError`: If cannot traverse or create path due to type mismatch
- `IndexError`: If array index exceeds maximum allowed

**Side Effects:**
- Creates intermediate dictionaries and arrays as needed
- Auto-wraps dict values into ZeroDict instances
- May extend arrays with `None` values to reach target index
- May overwrite existing values with warning if type incompatible

**Examples:**

**Creating deep structures:**
```python
ed = ZeroDict({})

# Creates entire path automatically
ed.set_path("database.credentials.username", "admin")
ed.set_path("database.credentials.password", "secret")
ed.set_path("database.pool.min_size", 5)

# Result:
# {
#   "database": {
#     "credentials": {"username": "admin", "password": "secret"},
#     "pool": {"min_size": 5}
#   }
# }
```

**Array creation:**
```python
ed = ZeroDict({})

# Creates array and nested structure
ed.set_path("users[0].name", "Alice")
ed.set_path("users[0].email", "alice@example.com")
ed.set_path("users[1].name", "Bob")

# Arrays are auto-extended with None for gaps
ed.set_path("sparse[10]", "value")  # Creates array with 11 elements
# sparse = [None, None, None, None, None, None, None, None, None, None, "value"]
```

**Type conflicts:**
```python
ed = ZeroDict({"config": "simple_string"})

# Overwrites incompatible type with warning
ed.set_path("config.nested.value", 123)
# Warning: Overwriting key 'config' with incompatible type.
# Existing: str, Required: ZeroDict. Data will be lost: 'simple_string'
```

**Strict mode:**
```python
ed = ZeroDict({"existing": {"key": "value"}})

# Strict mode requires intermediate paths to exist
try:
    ed.set_path("new.path.value", 123, strict=True)
except KeyError as e:
    print("Intermediate path doesn't exist")

# Works when path exists
ed.set_path("existing.key", "new_value", strict=True)  # OK
```

---

### `delete_path(path, *, strict=False)`

Delete value at specified path.

**Parameters:**
- `path` (str): Dot notation path. Required.
- `strict` (bool): If `True`, raise exception if path not found. If `False`, return `False` silently. Default: `False`.

**Returns:**
- `bool`: `True` if deleted, `False` if not found (non-strict mode)

**Raises:**
- `ValueError`: If path is invalid or exceeds depth limit
- `KeyError`: If `strict=True` and key not found
- `TypeError`: If `strict=True` and cannot traverse path
- `IndexError`: If `strict=True` and array index out of range

**Side Effects:**
- For dict keys: removes the key entirely
- For array elements: removes the element from the list (shifts subsequent indices)

**Examples:**

**Deleting dict keys:**
```python
ed = ZeroDict({"user": {"name": "Alice", "email": "alice@example.com"}})

# Delete nested key
ed.delete_path("user.email")
# Result: {"user": {"name": "Alice"}}

# Delete entire subtree
ed.delete_path("user")
# Result: {}
```

**Deleting array elements:**
```python
ed = ZeroDict({"items": [{"id": 1}, {"id": 2}, {"id": 3}]})

# Removes element from list (shifts subsequent indices)
ed.delete_path("items[1]")
# Result: {"items": [{"id": 1}, {"id": 3}]}
```

**Missing paths:**
```python
ed = ZeroDict({"data": "value"})

# Non-strict: returns False
result = ed.delete_path("missing")  # False

# Strict: raises exception
try:
    ed.delete_path("missing", strict=True)
except KeyError:
    print("Key not found")
```

---

## Batch Operations

### `set_many(updates, *, strict=False)`

Atomically apply multiple path updates. If any update fails, all changes are rolled back.

**Parameters:**
- `updates` (dict[str, Any]): Dictionary mapping paths to values. Required.
- `strict` (bool): If `True`, require all intermediate paths to exist. If `False`, create them as needed. Default: `False`.

**Returns:**
- None

**Raises:**
- Any exception from individual `set_path()` calls causes complete rollback
- `RuntimeWarning`: If rollback itself fails (data may be inconsistent)

**Side Effects:**
- Uses selective backup strategy (backs up only modified paths, not entire structure)
- On error, attempts to restore original values
- All updates are either fully applied or fully rolled back

**Performance:**
- Memory complexity: O(m) where m = size of updates, not O(n) where n = total data size
- Scales with update size, not total data size

**Examples:**

**Successful batch update:**
```python
config = ZeroDict({"app": {"name": "MyApp"}})

config.set_many({
    "app.version": "1.0.0",
    "app.debug": False,
    "features.analytics": True,
    "features.logging.level": "INFO"
})

# All updates applied atomically
```

**Rollback on error:**
```python
ed = ZeroDict({"count": 10, "status": "active"})

# Cause error with invalid path
try:
    ed.set_many({
        "count": 20,           # Would succeed
        "status": "inactive",  # Would succeed
        "..invalid": "value"   # Fails: invalid path
    })
except ValueError:
    pass

# All changes rolled back
assert ed.get_path("count") == 10      # Original value preserved
assert ed.get_path("status") == "active"  # Original value preserved
```

**Complex batch operations:**
```python
ed = ZeroDict({})

# Create complex structure in one atomic operation
ed.set_many({
    "services[0].name": "API",
    "services[0].endpoints[0].url": "https://api.example.com",
    "services[0].endpoints[0].timeout": 30,
    "services[0].endpoints[1].url": "https://backup.example.com",
    "services[1].name": "Database",
    "services[1].connection.host": "db.example.com",
    "services[1].connection.port": 5432
})
```

---

### `move(source_path, dest_path, *, strict=False)`

Move or rename a field from source to destination atomically.

**Parameters:**
- `source_path` (str): Path of field to move. Required.
- `dest_path` (str): Destination path. Required.
- `strict` (bool): If `True`, fail if source missing or dest exists. If `False` (default), silently succeed if source missing, overwrite dest if exists. Default: `False`.

**Returns:**
- None

**Raises:**
- `ValueError`: If paths invalid, empty, same, or would create circular reference
- `KeyError`: If `strict=True` and source doesn't exist or dest exists
- `TypeError`: If value contains non-serializable objects (cannot deepcopy)

**Side Effects:**
- Atomically copies value from source to dest, then deletes source
- Creates intermediate paths at destination as needed
- Uses deepcopy for value safety (changes to moved value don't affect original location)
- On error, attempts rollback to restore both source and destination

**Examples:**

**Rename within same parent:**
```python
ed = ZeroDict({"section": {"old_name": "value", "other": "data"}})

ed.move("section.old_name", "section.new_name")
# Result: {"section": {"new_name": "value", "other": "data"}}
```

**Move to different location:**
```python
ed = ZeroDict({"temp": "important_value", "permanent": {}})

ed.move("temp", "permanent.data")
# Result: {"permanent": {"data": "important_value"}}
```

**Move array elements:**
```python
ed = ZeroDict({
    "inbox": [{"id": 1, "msg": "Hello"}],
    "archive": []
})

ed.move("inbox[0]", "archive[0]")
# Result: inbox is now [] (element popped, list shrinks),
#         archive is now [{"id": 1, "msg": "Hello"}].
# delete_path on an array element pops it — subsequent indices shift left.
```

**Circular reference prevention:**
```python
ed = ZeroDict({"a": {"b": {"c": "value"}}})

# Cannot move parent into its own child
try:
    ed.move("a", "a.b.new_location")
except ValueError as e:
    print("Would create circular reference")
```

**Non-strict mode (default):**
```python
ed = ZeroDict({"existing": "value", "target": "old_value"})

# Overwrite destination (default behavior)
ed.move("existing", "target")
# Result: {"target": "value"}

# Silent success if source missing
ed.move("nonexistent", "somewhere")
# No error, no changes
```

---

## Comparison and Change Tracking

### `diff(other)`

Generate detailed list of changes between two ZeroDict instances.

**Parameters:**
- `other` (ZeroDict): ZeroDict to compare against. Required.

**Returns:**
- `list[dict[str, Any]]`: List of change operations, each with:
  - `"op"`: Operation type (`"add"`, `"remove"`, `"replace"`)
  - `"path"`: Path where change occurred
  - `"before"`: Previous value (for `"remove"` and `"replace"`)
  - `"after"`: New value (for `"add"` and `"replace"`)

**Raises:**
- `ValueError`: If circular reference detected or depth exceeds limit

**Side Effects:**
- None (read-only operation)

**Examples:**

**Basic changes:**
```python
original = ZeroDict({"price": 100, "stock": 50})
modified = ZeroDict({"price": 120, "stock": 45, "discount": 10})

changes = original.diff(modified)
# [
#   {"op": "replace", "path": "price", "before": 100, "after": 120},
#   {"op": "replace", "path": "stock", "before": 50, "after": 45},
#   {"op": "add", "path": "discount", "after": 10}
# ]
```

**Nested structure changes:**
```python
original = ZeroDict({
    "user": {"name": "Alice", "email": "alice@old.com"},
    "settings": {"theme": "light"}
})

modified = ZeroDict({
    "user": {"name": "Alice", "email": "alice@new.com", "phone": "123"},
    "settings": {"theme": "dark", "language": "en"}
})

changes = original.diff(modified)
# Shows:
# - replaced: user.email
# - added: user.phone
# - replaced: settings.theme
# - added: settings.language
```

**Array changes:**
```python
original = ZeroDict({"items": [1, 2, 3]})
modified = ZeroDict({"items": [1, 5, 3, 4]})

changes = original.diff(modified)
# [
#   {"op": "replace", "path": "items[1]", "before": 2, "after": 5},
#   {"op": "add", "path": "items[3]", "after": 4}
# ]
```

**Note on deleted array elements:**
```python
ed = ZeroDict({"arr": [1, 2, 3]})
ed.delete_path("arr[1]")  # Removes element, arr becomes [1, 3]

changes = ZeroDict({"arr": [1, 2, 3]}).diff(ed)
# Shows:
# {"op": "replace", "path": "arr[1]", "before": 2, "after": 3}
# {"op": "remove", "path": "arr[2]", "before": 3}
# (Element removed, so indices shift — diff compares by position)
```

---

### `__eq__(other)` / `__ne__(other)`

Compare ZeroDict with another ZeroDict or plain dict for equality.

**Parameters:**
- `other` (object): Object to compare with

**Returns:**
- `bool`: `True` if equal, `False` otherwise

**Raises:**
- `ValueError`: If comparison depth exceeds maximum nesting depth

**Side Effects:**
- None (read-only operation)

**Examples:**

**Basic comparison:**
```python
ed1 = ZeroDict({"a": 1, "b": 2})
ed2 = ZeroDict({"a": 1, "b": 2})
plain = {"a": 1, "b": 2}

assert ed1 == ed2           # True
assert ed1 == plain         # True (duck typing)
assert ed1 != {"a": 999}    # True
```

**Nested comparison:**
```python
ed1 = ZeroDict({"user": {"profile": {"name": "Alice"}}})
ed2 = ZeroDict({"user": {"profile": {"name": "Alice"}}})

assert ed1 == ed2  # True (deep comparison)
```

---

## Serialization

### `to_dict()`

Convert ZeroDict to plain Python dictionary recursively.

**Parameters:**
- None

**Returns:**
- `dict[str, Any]`: Plain dictionary with all nested ZeroDict instances converted to dicts

**Raises:**
- `ValueError`: If circular reference detected or depth exceeds limit

**Side Effects:**
- None (creates new dict, doesn't modify original)

**Examples:**

**Basic conversion:**
```python
ed = ZeroDict({"user": {"name": "Alice", "age": 30}})
plain = ed.to_dict()

assert isinstance(plain, dict)
assert not isinstance(plain, ZeroDict)
assert plain == {"user": {"name": "Alice", "age": 30}}
```

**Nested structures:**
```python
ed = ZeroDict({
    "data": [
        {"id": 1, "nested": {"value": "x"}},
        {"id": 2, "nested": {"value": "y"}}
    ]
})

plain = ed.to_dict()
# All ZeroDict instances converted to plain dicts
# Arrays preserved as lists
# Primitive values unchanged
```

---

### `from_dict(d)`

Static method to create ZeroDict from plain dictionary.

**Parameters:**
- `d` (dict[str, Any]): Plain dictionary. Required.

**Returns:**
- `ZeroDict`: New ZeroDict instance

**Raises:**
- Same validation as `ZeroDict()` constructor

**Side Effects:**
- Same as constructor

**Examples:**

```python
plain = {"user": {"name": "Alice"}}
ed = ZeroDict.from_dict(plain)

assert isinstance(ed, ZeroDict)
assert ed.get_path("user.name") == "Alice"
```

---

### `to_json(**kwargs)`

Convert ZeroDict to JSON string with customizable formatting.

**Parameters:**
- `**kwargs`: Passed to `json.dumps()`. Common options:
  - `indent` (int | None): Number of spaces for indentation. Default: `2`
  - `ensure_ascii` (bool): Escape non-ASCII characters. Default: `False`
  - `sort_keys` (bool): Sort keys alphabetically. Default: `False`

**Returns:**
- `str`: JSON string representation

**Raises:**
- `json.JSONEncodeError`: If data contains non-serializable objects
- `ValueError`: If circular reference detected

**Side Effects:**
- None

**Examples:**

**Default formatting:**
```python
ed = ZeroDict({"name": "Alice", "age": 30})
json_str = ed.to_json()
# '{\n  "name": "Alice",\n  "age": 30\n}'
```

**Compact formatting:**
```python
ed = ZeroDict({"data": [1, 2, 3]})
compact = ed.to_json(indent=None)
# '{"data":[1,2,3]}'
```

**Custom formatting:**
```python
ed = ZeroDict({"user": "Alice", "status": "active"})
sorted_json = ed.to_json(sort_keys=True, indent=4)
# Keys alphabetically sorted, 4-space indentation
```

---

### `from_json(s)`

Static method to create ZeroDict from JSON string.

**Parameters:**
- `s` (str): JSON string. Required.

**Returns:**
- `ZeroDict`: New ZeroDict instance

**Raises:**
- `json.JSONDecodeError`: If JSON is malformed
- Same validation as `ZeroDict()` constructor

**Side Effects:**
- Same as constructor

**Examples:**

```python
json_str = '{"user": {"name": "Alice", "age": 30}}'
ed = ZeroDict.from_json(json_str)

assert ed.get_path("user.name") == "Alice"
assert ed.get_path("user.age") == 30
```

---

## Dictionary Interface Methods

ZeroDict implements the standard Python dictionary interface.

### `len(zd)` / `__len__()`

**Returns:** Number of keys at top level

```python
ed = ZeroDict({"a": 1, "b": 2, "c": {"nested": 3}})
assert len(ed) == 3
```

---

### `key in zd` / `__contains__(key)`

**Returns:** `True` if key exists at top level, `False` otherwise

```python
ed = ZeroDict({"a": 1, "nested": {"b": 2}})
assert "a" in ed         # True
assert "nested" in ed    # True
assert "b" in ed         # False (not at top level)
```

---

### `zd[key]` / `__getitem__(key)`

Get item using bracket notation. Similar to dot notation but raises `KeyError` if key doesn't exist.

```python
ed = ZeroDict({"name": "Alice"})
print(ed["name"])   # "Alice"
print(ed["missing"])  # KeyError
```

---

### `zd[key] = value` / `__setitem__(key, value)`

Set item using bracket notation. Value will be auto-wrapped if dict or list.

```python
ed = ZeroDict({})
ed["name"] = "Alice"
ed["profile"] = {"age": 30}  # Auto-wrapped to ZeroDict
```

---

### `del zd[key]` / `__delitem__(key)`

Delete item using bracket notation.

```python
ed = ZeroDict({"a": 1, "b": 2})
del ed["a"]
assert "a" not in ed
```

---

### `iter(zd)` / `__iter__()`

Iterate over keys at top level.

```python
ed = ZeroDict({"a": 1, "b": 2})
for key in ed:
    print(key)  # "a", then "b"
```

---

### `zd.keys()`, `zd.values()`, `zd.items()`

Standard dictionary view methods.

```python
ed = ZeroDict({"a": 1, "b": 2})

list(ed.keys())    # ["a", "b"]
list(ed.values())  # [1, 2]
list(ed.items())   # [("a", 1), ("b", 2)]
```

---

### `zd.get(key, default=None)`

Get value for key with default. Similar to `dict.get()`.

```python
ed = ZeroDict({"name": "Alice"})
print(ed.get("name"))         # "Alice"
print(ed.get("missing"))      # None
print(ed.get("missing", "N/A"))  # "N/A"
```

---

### `zd.pop(key, *args)`

Remove and return value for key.

```python
ed = ZeroDict({"a": 1, "b": 2})
value = ed.pop("a")  # Returns 1, removes key
print(value)         # 1
assert "a" not in ed

# With default
value = ed.pop("missing", "default")  # "default"
```

---

### `zd.update(other)`

Update with key-value pairs from another dict or ZeroDict.

```python
ed = ZeroDict({"a": 1})
ed.update({"b": 2, "c": 3})
# Result: {"a": 1, "b": 2, "c": 3}
```

---

### `zd.clear()`

Remove all items.

```python
ed = ZeroDict({"a": 1, "b": 2})
ed.clear()
assert len(ed) == 0
```

---

### `zd.setdefault(key, default=None)`

Get value for key, setting it to default if it doesn't exist.

```python
ed = ZeroDict({"count": 5})
value = ed.setdefault("count", 0)  # Returns 5 (exists)
value = ed.setdefault("new", 10)   # Returns 10 (sets and returns)
assert ed["new"] == 10
```

---

### `zd.contains_key(key)`

Check if key exists. Useful to distinguish between `None` value and missing key.

```python
ed = ZeroDict({"a": None, "b": 1})
assert ed.contains_key("a")  # True (exists with None value)
assert ed.contains_key("b")  # True
assert not ed.contains_key("c")  # False (doesn't exist)

# Prefer 'in' operator for simple cases
assert "a" in ed  # Same as contains_key("a")
```

---

### `zd.copy(deep=True)`

Create a copy of the ZeroDict.

**Parameters:**
- `deep` (bool): If `True`, create deep copy. If `False`, create shallow copy. Default: `True`.

**Returns:**
- `ZeroDict`: New instance

**Raises:**
- `TypeError`: If `deep=True` and data contains non-serializable objects

**Examples:**

**Deep copy (default):**
```python
original = ZeroDict({"nested": {"value": 1}})
copied = original.copy()

copied.nested.value = 999
assert original.nested.value == 1  # Independent
```

**Shallow copy:**
```python
original = ZeroDict({"nested": {"value": 1}})
shallow = original.copy(deep=False)

shallow.nested.value = 999
assert original.nested.value == 999  # Shared reference
```

---

### `repr(zd)` / `__repr__()`

String representation of the ZeroDict for debugging and logging.

**Returns:**
- `str`: Formatted as `ZeroDict({...})` with the internal dict representation.

**Behavior:**
- Output is truncated to ~500 characters for large structures, showing an approximate key count.
- Circular references are handled gracefully and rendered as `<circular reference, N keys>`.

**Examples:**

```python
ed = ZeroDict({"name": "Alice", "age": 30})
print(repr(ed))  # ZeroDict({'name': 'Alice', 'age': 30})

# Large structures are truncated
large = ZeroDict({f"key_{i}": i for i in range(1000)})
print(repr(large))
# ZeroDict({'key_0': 0, 'key_1': 1, ... [showing ~N of 1000 keys])
```

---

## Security and Validation

### Key Validation Function

The `Validator.validate_key(key)` function in `validator.py` validates all keys according to security rules. You don't call this directly, but it's invoked automatically on all key operations.

**Validation rules:**
- Key cannot be empty
- Must be valid ASCII (no emoji, accented characters)
- Maximum 1000 bytes (encoded UTF-8)
- Only allowed characters: letters, numbers, underscore, hyphen
- Reserved characters (`.`, `[`, `]`) not allowed

**Error messages are descriptive:**
```python
# Empty key
ZeroDict({"": "value"})
# ValueError: Key cannot be empty

# Non-ASCII
ZeroDict({"café": "value"})
# ValueError: Key 'café' contains non-ASCII character(s): ['é'].
# Only ASCII letters, numbers, underscore, and hyphen are allowed.

# Reserved characters
ZeroDict({"user.name": "value"})
# ValueError: Key 'user.name' contains invalid character(s): ['.'].
# Keys can only contain ASCII letters, numbers, underscore, and hyphen.
# Reserved characters (. [ ]) are used by path API.
# Use set_path() to create nested structures.
```

### Circular Reference Protection

ZeroDict automatically detects and prevents circular references during:
- Construction (`ZeroDict(data)`)
- Wrapping (`ZeroDict._wrap()`)
- Serialization (`Serializer.to_dict()`)
- Comparison (`DiffEngine.compare()`)
- Diff (`DiffEngine.diff()`)

**Example:**
```python
# Circular list
lst = []
lst.append(lst)
try:
    ZeroDict({"list": lst})
except ValueError as e:
    print(e)  # "Circular reference detected in input list"

# Circular dict
data = {}
data["self"] = data
try:
    ZeroDict(data)
except ValueError as e:
    print(e)  # "Circular reference detected in input dict"
```

### Depth Limit Protection

All operations that traverse structures enforce `MAX_NESTING_DEPTH = 100`:

```python
ed = ZeroDict({})

# Create path with 200 levels
deep_path = ".".join(["level"] * 200)
try:
    ed.set_path(deep_path, "value")
except ValueError as e:
    print(e)
    # "Path depth 200 exceeds maximum nesting depth 100.
    # Path: 'level.level.level...'"
```

### Size Limit Protection

Values are checked against `MAX_VALUE_SIZE = 10_000_000` bytes (10MB):

```python
# Single huge string
huge = "x" * 20_000_000  # 20MB
try:
    ZeroDict({"data": huge})
except ValueError as e:
    print(e)
    # "Value size (20,000,000 bytes) exceeds maximum allowed (10,000,000 bytes).
    # Consider splitting into smaller structures."
```

---

## MissingPath Sentinel

### What is MissingPath?

`MissingPath` is a sentinel object returned when accessing non-existent paths with dot notation. It behaves like `None` in boolean contexts but provides clear error messages for invalid operations.

**Key characteristics:**
- Falsy in boolean context (`not missing` is `True`)
- Equals `None` (`missing == None` is `True`)
- **NOT identical to None** (`missing is None` is `False`)
- Hashable (can be used in sets/dicts)
- JSON serializable (converts to `None`)

### Usage Patterns

**Boolean checks:**
```python
ed = ZeroDict({"existing": "value"})

if ed.missing:
    print("Has value")  # Not executed
else:
    print("Missing or None")  # Executed

# Prefer existence check
if "missing" in ed:
    print("Exists")
else:
    print("Does not exist")  # Executed
```

**Comparison with None:**
```python
missing = ed.missing_key

# Use == for comparison, NOT is
assert missing == None   # ✓ True
assert missing is None   # ✗ False (Python limitation)

# Type check
assert isinstance(missing, MissingPath)  # True
```

**Error on assignment:**
```python
ed = ZeroDict({})

# Clear error message
try:
    ed.missing.deep.path = "value"
except AttributeError as e:
    print(e)
    # "Cannot set attribute 'path' on missing path 'missing.deep.path'.
    # Path 'missing.deep.path' does not exist.
    # Use set_path() to create deep paths, or ensure parent path exists first."
```

**Chaining (limited depth):**
```python
ed = ZeroDict({})

# Can chain up to MAX_MISSING_PATH_DEPTH (100) levels
deep = ed.a.b.c.d.e.f.g  # Returns MissingPath

# Warns if exceeding depth
# (This protects against infinite loops in buggy code)
```

**Pickle/JSON serialization:**
```python
import pickle
import json

ed = ZeroDict({})
missing = ed.missing

# Pickle: converts to None
pickled = pickle.dumps(missing)
unpickled = pickle.loads(pickled)
assert unpickled is None

# JSON: MissingPath values converted to None
ed2 = ZeroDict({"value": "x"})
ed2._data["missing"] = ed.missing  # Normally not done directly
json_str = ed2.to_json()
# {"value": "x", "missing": null}
```

---

## Error Handling Patterns

### Common Exceptions

**ValueError:**
- Invalid paths (empty, consecutive dots, leading/trailing dots)
- Exceeding limits (depth, size, array index)
- Circular references
- Invalid key characters

**KeyError:**
- Missing keys in strict mode
- Missing paths in move/delete with strict mode

**TypeError:**
- Non-dict passed to constructor
- Non-string keys
- Cannot traverse non-dict/non-list in strict mode
- Cannot deepcopy non-serializable objects

**IndexError:**
- Array index out of range in strict mode
- Array index exceeds MAX_ARRAY_INDEX

### Error Handling Best Practices

**Use strict mode for validation:**
```python
def process_config(data: dict) -> None:
    ed = ZeroDict(data)

    # Validate required fields exist
    try:
        db_host = ed.get_path("database.host", strict=True)
        db_port = ed.get_path("database.port", strict=True)
    except KeyError as e:
        raise ValueError(f"Missing required config: {e}")

    # Process with validated data
    connect(host=db_host, port=db_port)
```

**Use non-strict mode with defaults:**
```python
def get_config_value(ed: ZeroDict, path: str, default: Any) -> Any:
    # Safe access with fallback
    return ed.get_path(path, default=default)

# Usage
timeout = get_config_value(config, "api.timeout", default=30)
```

**Atomic operations with rollback:**
```python
def update_user_profile(user_data: ZeroDict, updates: dict[str, Any]) -> None:
    try:
        user_data.set_many(updates)
        print("Profile updated successfully")
    except Exception as e:
        # Automatic rollback occurred
        print(f"Update failed: {e}")
        # Original data preserved
```

---

## Performance Considerations

### Memory Usage

**Wrapping overhead:**
- Each nested dict becomes a ZeroDict instance
- Small memory overhead per instance (~200 bytes)
- Use `to_dict()` for memory-sensitive serialization

**Selective backup in set_many():**
- Only backs up modified paths
- Memory: O(update_size), not O(total_data_size)
- Scales with update size, not total size

### Best Practices

**Avoid excessive nesting:**
```python
# Good: reasonable depth
ed.set_path("user.profile.name", "Alice")

# Bad: very deep nesting (slow, memory intensive)
ed.set_path("a.b.c.d.e.f.g.h.i.j.k.l.m", "value")
```

**Batch updates when possible:**
```python
# Good: single atomic operation
ed.set_many({
    "field1": value1,
    "field2": value2,
    "field3": value3
})

# Less efficient: multiple individual operations
ed.set_path("field1", value1)
ed.set_path("field2", value2)
ed.set_path("field3", value3)
```

**Use shallow copy when appropriate:**
```python
# Deep copy (default): safe but slower
full_copy = ed.copy()

# Shallow copy: fast but shared references
quick_copy = ed.copy(deep=False)
```

---

## Thread Safety

**ZeroDict is NOT thread-safe.** Use external synchronization for concurrent access.

**Example with threading.Lock:**
```python
import threading
from zerodict import ZeroDict

shared_config = ZeroDict({})
lock = threading.RLock()

def update_config(key: str, value: Any) -> None:
    with lock:
        shared_config.set_path(key, value)

def read_config(key: str) -> Any:
    with lock:
        return shared_config.get_path(key)
```

**Example with queue for producer-consumer:**
```python
import queue
import threading
from zerodict import ZeroDict

config_queue = queue.Queue()

def producer():
    for i in range(10):
        config_queue.put(("key" + str(i), i))

def consumer(shared: ZeroDict):
    while True:
        key, value = config_queue.get()
        if key is None:
            break
        shared.set_path(key, value)
        config_queue.task_done()
```

**Async (asyncio) does NOT require locks** unless using threads.

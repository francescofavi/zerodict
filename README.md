<p align="center">
  <img src="https://raw.githubusercontent.com/francescofavi/zerodict/main/logo.png" alt="ZeroDict logo" width="200">
</p>

# ZeroDict

[![CI](https://img.shields.io/github/actions/workflow/status/francescofavi/zerodict/ci.yml?branch=main&label=CI&cacheSeconds=0)](https://github.com/francescofavi/zerodict/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zerodict.svg?cacheSeconds=0)](https://pypi.org/project/zerodict/)
[![Python versions](https://img.shields.io/pypi/pyversions/zerodict.svg?cacheSeconds=0)](https://pypi.org/project/zerodict/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?cacheSeconds=0)](https://github.com/francescofavi/zerodict/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/zerodict.svg?cacheSeconds=0)](https://pypi.org/project/zerodict/)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg?cacheSeconds=0)](https://peps.python.org/pep-0561/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg?cacheSeconds=0)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?cacheSeconds=0)](https://docs.astral.sh/ruff/)

**Safe, explicit, and powerful manipulation of nested dict structures in Python.**

ZeroDict is a zero-dependency dict wrapper for Python 3.11+ that makes working with nested data structures safe, explicit, and predictable. It eliminates the fragility of standard dicts without introducing the hidden side effects common in similar libraries.

---

## The Problem

Nested dictionaries are everywhere in Python: configuration files, API responses, data pipelines, document stores. Yet Python's built-in `dict` makes working with nested structures surprisingly painful.

**Reading is fragile.** Accessing a missing key crashes your program:

```python
config = {"database": {"host": "localhost"}}

config["cache"]["ttl"]  # KeyError: 'cache'
```

The standard workaround is `.get()` chains, which are verbose and hard to read:

```python
config.get("cache", {}).get("ttl")                          # one level
config.get("api", {}).get("endpoints", {}).get("users")     # two levels
config.get("a", {}).get("b", {}).get("c", {}).get("d")      # this gets old fast
```

Every nested access requires defensive code. Miss one `.get()` and you're back to `KeyError`.

**Writing is error-prone.** Creating nested structures requires manual initialization of every intermediate level:

```python
config["cache"] = {}
config["cache"]["redis"] = {}
config["cache"]["redis"]["host"] = "localhost"
config["cache"]["redis"]["port"] = 6379
```

Four lines to set two values. And if any intermediate key already exists with a non-dict value, you silently overwrite it.

**Existing alternatives trade one problem for another.** Libraries like `addict`, `munch`, and `easydict` solve the reading problem but introduce a worse one: they auto-create nested dicts on any attribute access, including writes. A simple typo silently creates garbage data:

```python
from addict import Dict
d = Dict()
d.databse.host = "localhost"  # Typo! 'databse' now exists as a real key
# No error, no warning. The bug hides until production.
```

This is particularly dangerous in configuration management and data pipelines, where a silent typo can propagate through your entire system before anyone notices.

---

## The Solution

ZeroDict solves both problems with a clear design principle: **safe reads, explicit writes**.

- **Reading** a missing path never crashes and never modifies your data. You get a falsy sentinel back, and your dict stays untouched.
- **Writing** a deep path requires an explicit call (`set_path`), so typos are caught immediately instead of creating phantom keys.

```python
from zerodict import ZeroDict

config = ZeroDict({"database": {"host": "localhost"}})

# Reading: safe, no crashes, no side effects
print(config.database.host)       # "localhost"
print(config.cache.ttl)           # None-like sentinel (no KeyError!)
print(config.a.b.c.d.e)           # Still safe, still no crash

# Writing: explicit intent required for deep paths
config.set_path("cache.redis.host", "localhost")   # Creates entire path in one call
config.set_path("cache.redis.port", 6379)

# Typos are caught, not hidden
config.databse.host = "localhost"  # AttributeError: 'databse' doesn't exist
```

This is not just syntactic sugar. It is a fundamentally different approach: reads are permissive (your code doesn't crash on optional fields), writes are strict (your code doesn't silently create wrong data).

---

## What ZeroDict Gives You

**Path API with dot notation and array support.** Navigate and manipulate nested structures with string paths instead of chained bracket access:

```python
config.set_path("api.endpoints.users", "/v1/users")
config.set_path("servers[0].host", "prod-1")
value = config.get_path("api.endpoints.users")
config.delete_path("servers[0].host")
```

**Atomic batch updates.** Update multiple paths at once with all-or-nothing semantics. If any path fails validation, all changes are rolled back automatically:

```python
config.set_many({
    "db.host": "localhost",
    "db.port": 5432,
    "cache.ttl": 3600,
})
# All succeed, or none do. No partial state.
```

**Change tracking.** Compare two structures and get a precise list of what changed:

```python
changes = original.diff(modified)
# [{"op": "replace", "path": "price", "before": 100, "after": 120},
#  {"op": "add", "path": "discount", "after": 10}]
```

**Security by default.** Built-in protections prevent abuse when handling untrusted data: nesting depth limits, array index bounds, key format validation, value size caps, and circular reference detection. These are not optional add-ons; they are always active.

**Zero dependencies.** ZeroDict uses only the Python standard library. No transitive dependency tree, no version conflicts, no supply chain risk. It installs in milliseconds and adds nothing to your dependency audit.

**Full dict compatibility.** ZeroDict supports the standard dict interface (`len`, `in`, `keys`, `values`, `items`, `get`, `pop`, `update`, iteration). You can use it anywhere a dict-like object is expected, and convert back to a plain dict at any time with `to_dict()`.

---

## Who Should Use ZeroDict

ZeroDict is designed for any scenario where you work with nested dictionaries and want predictable, safe behavior:

- **Configuration management**: load config files (JSON, YAML parsed to dict) and access nested settings without defensive `.get()` chains. Batch-update multiple settings atomically.
- **API response processing**: access deeply nested fields in API responses without worrying about optional or missing keys. No more `response.get("data", {}).get("user", {}).get("email")`.
- **Data transformation pipelines**: reshape nested structures with path-based set/get/delete/move operations. Track changes with `diff()`.
- **Prototyping and exploration**: quickly build and manipulate nested data in notebooks or scripts without boilerplate.
- **Any application handling untrusted nested data**: the built-in security limits protect against pathological inputs without additional code.

---

## Comparison with Other Libraries

| Feature | ZeroDict | addict | python-box | munch | easydict |
|---------|:--------:|:------:|:----------:|:-----:|:--------:|
| Safe reading (no KeyError) | yes | yes | yes | yes | yes |
| Explicit deep writes | yes | no | no | no | no |
| Path API (`a.b.c`, `arr[0]`) | yes | no | no | no | no |
| Atomic batch updates | yes | no | no | no | no |
| Move/rename fields | yes | no | no | no | no |
| Deep diff tracking | yes | no | no | no | no |
| Security limits | yes | no | no | no | no |
| Type hints | Full | Partial | Partial | No | No |
| Circular ref protection | yes | no | yes | no | no |

**vs addict/munch/easydict:** Auto-create nested dicts on write, which means typos silently create garbage keys. ZeroDict requires explicit `set_path()` for deep writes.

**vs python-box:** Feature-rich but complex. ZeroDict is focused: safe access + path manipulation + atomic operations, with clear semantics and no magic.

**vs plain dicts:** ZeroDict adds safety, path API, and atomic operations while maintaining full dict compatibility.

---

## Installation

**Requirements:** Python 3.11+ | No external dependencies (standard library only)

```bash
pip install zerodict
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add zerodict
```

---

## Quick Start

```python
from zerodict import ZeroDict

# Create from dict
config = ZeroDict({
    "database": {
        "host": "localhost",
        "port": 5432
    }
})

# Safe reading (no KeyError)
print(config.database.host)  # "localhost"
print(config.cache)          # None-like (no crash!)

# Simple first-level writes
config.new_field = "value"

# Explicit deep writes via Path API
config.set_path("api.endpoints.users", "/api/v1/users")
config.set_path("api.timeout", 30)

# Array support
config.set_path("servers[0].name", "prod-1")
config.set_path("servers[0].ip", "192.168.1.100")

# Atomic batch updates (all-or-nothing)
config.set_many({
    "cache.enabled": True,
    "cache.ttl": 3600,
    "logging.level": "INFO"
})

# Export to dict or JSON
print(config.to_json())
data = config.to_dict()
```

---

## Core Features

### Safe Reading with Dot Notation

```python
data = ZeroDict({"user": {"name": "John"}})

# Existing paths work as expected
print(data.user.name)      # "John"

# Missing paths return None-like sentinel (no KeyError)
print(data.user.email)     # None
print(data.missing.deep)   # None

# Check existence
if "email" in data.user:
    print("Has email")
```

### Path API for Deep Creation

```python
config = ZeroDict({})

# Create nested structures in one call
config.set_path("database.credentials.username", "admin")
config.set_path("database.pool.min_size", 5)

# Read with paths
value = config.get_path("database.credentials.username")

# With defaults
ttl = config.get_path("cache.ttl", default=3600)

# Delete with paths
config.delete_path("database.pool.min_size")
```

### Array Manipulation

```python
data = ZeroDict({})

# Create and access array elements
data.set_path("items[0].id", 1)
data.set_path("items[0].name", "Item 1")
data.set_path("items[1].id", 2)

# Arrays auto-extend with None padding
data.set_path("arr[5]", "value")  # Creates arr with 6 elements

# Read array elements
first_name = data.get_path("items[0].name")
```

### Atomic Batch Updates

All updates succeed or all fail (automatic rollback on error):

```python
config = ZeroDict({"balance": 1000})

try:
    config.set_many({
        "balance": 900,
        "transactions[0].amount": -100,
        "invalid..path": "this will fail"  # Invalid path causes rollback
    })
except ValueError:
    # ALL changes rolled back
    print(config.balance)  # 1000 (unchanged)
```

### Move/Rename Fields

Atomically relocate or rename fields:

```python
config = ZeroDict({
    "temp_data": {"user_id": 123, "session": "abc"},
    "permanent": {}
})

# Move entire subtree
config.move("temp_data", "permanent.user_session")
# Result: {"permanent": {"user_session": {"user_id": 123, "session": "abc"}}}
```

### Change Tracking

Track what changed between dict states:

```python
original = ZeroDict({"price": 100, "stock": 50})
modified = ZeroDict({"price": 120, "stock": 45, "discount": 10})

changes = original.diff(modified)
for change in changes:
    print(f"{change['op']}: {change['path']}")
    # replace: price
    # replace: stock
    # add: discount
```

### Strict Mode

Control error handling per-operation:

```python
data = ZeroDict({"user": {"name": "John"}})

# Default: returns None for missing paths
value = data.get_path("user.email")  # None

# Strict mode: raises exceptions
try:
    value = data.get_path("user.email", strict=True)
except KeyError:
    print("Path not found!")
```

### Serialization

```python
ed = ZeroDict({"name": "Alice", "age": 30})

# JSON round-trip
json_str = ed.to_json()
loaded = ZeroDict.from_json(json_str)

# Plain dict round-trip
plain = ed.to_dict()
back = ZeroDict.from_dict(plain)
```

---

## Advanced Usage

### Distinguishing None from Missing Keys

```python
ed = ZeroDict({"a": None})

# Both appear None-like
ed.a        # None (key exists with None value)
ed.missing  # MissingPath (key doesn't exist)

# Use 'in' to distinguish
"a" in ed        # True
"missing" in ed  # False
```

### Deep vs Shallow Copy

```python
original = ZeroDict({"nested": {"value": 1}})

# Deep copy (default): independent
copied = original.copy()
copied.nested.value = 999
assert original.nested.value == 1  # Unchanged

# Shallow copy: shared references
shallow = original.copy(deep=False)
shallow.nested.value = 888
assert original.nested.value == 888  # Shared!
```

### Thread Safety

ZeroDict is **NOT thread-safe**. For concurrent access:

```python
import threading

zd = ZeroDict({})
lock = threading.RLock()

with lock:
    zd.set_path("counter", zd.get_path("counter", default=0) + 1)
```

Async code (asyncio) does not require locks unless using actual threads.

---

## Known limits and open issues

Where the project is deliberately limited, where it enforces a hard constraint, and what is not yet shipped — one list, grouped by axis (`design:` intentional trade-off, `limit:` hard constraint visible in code, `open:` tracked roadmap item).

- *design:* Explicit `set_path()` required for deep writes — no auto-creation on attribute access (the opposite of addict/munch; typos surface as errors rather than phantom keys).
- *design:* Not thread-safe — concurrent writers must coordinate with an external lock (RLock).
- *design:* `copy()` is deep by default — shallow copy (`copy(deep=False)`) shares nested references on purpose.
- *limit:* Security limits are always on (nesting depth, array index bounds, key format, value size, circular refs) — not opt-out.
- *limit:* Path expression grammar covers `a.b.c` + `arr[0]` only — no wildcards, no slicing, no predicates.
- *limit:* `to_json()` requires every value to be JSON-serializable — non-JSON values must be converted first.
- *limit:* `set_many()` is all-or-nothing — any invalid path rolls back every other update in the batch.
- *open:* No observable roadmap items tracked in code as of the current release.

## Anti-patterns — how NOT to use this project

Usage patterns that reliably cause trouble:

- Do not expect addict/munch-style attribute auto-creation — deep writes must go through `set_path()`.
- Do not share a ZeroDict instance across threads without an external lock.
- Do not call `copy(deep=False)` when you plan to mutate nested structures — the shallow copy shares references with the original.
- Do not store non-JSON-serializable values (`set`, custom classes, raw `datetime`) in a ZeroDict you later `to_json()`.
- Do not use `is None` to detect a missing path — `MissingPath() is None` is False; use `== None`, `not value`, or `"key" in zd` instead.
- Do not bundle independent updates in `set_many()` — a single invalid path rolls back the entire batch.
- Do not assume array auto-extension preserves value types — gaps are padded with `None`.

---

## Development Setup

```bash
git clone https://github.com/francescofavi/zerodict.git
cd zerodict
uv sync
```

### Running Tests

```bash
uv run pytest
```

### Running Examples

```bash
uv run python examples/demo.py
```

See [Development](https://github.com/francescofavi/zerodict/blob/main/docs/DEVELOPMENT.md) for full setup instructions, pre-commit hooks, and commit conventions.

---

## Further Documentation

- **[API Reference](https://github.com/francescofavi/zerodict/blob/main/docs/API_REFERENCE.md)** - Complete reference for all public APIs, parameters, and advanced usage patterns
- **[Architecture](https://github.com/francescofavi/zerodict/blob/main/docs/ARCHITECTURE.md)** - Internal module structure, responsibilities, boundaries, and data flow
- **[Anti-Patterns](https://github.com/francescofavi/zerodict/blob/main/docs/ANTI_PATTERNS.md)** - Common mistakes and how to avoid them
- **[Development](https://github.com/francescofavi/zerodict/blob/main/docs/DEVELOPMENT.md)** - Setup for contributors, running tests, and running examples

## Contributing

This repository is maintained as a personal portfolio project. Pull requests are generally not accepted, but exceptional contributions may be considered.

For bug reports and feature requests, please use [GitHub Issues](https://github.com/francescofavi/zerodict/issues).

## License

[MIT License](https://github.com/francescofavi/zerodict/blob/main/LICENSE) - Copyright (c) 2025 Francesco Favi

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

**Nested dicts without the boilerplate: dot-notation reads/writes, deep path API, structural diffs, atomic updates. Pure stdlib, zero runtime dependencies.**

ZeroDict wraps Python dicts so missing paths never crash your code, and deep writes never silently create phantom keys from typos. Reads are permissive, writes are strict — a deliberate inversion of how `addict`, `munch`, and `easydict` behave. It targets developers working with configuration files, API responses, and nested data pipelines who want predictable semantics without pulling in a dependency tree.

### Key Value Points

- **Safe reads.** Missing nested paths return a falsy sentinel instead of raising `KeyError`, and the underlying dict is never mutated as a side effect.
- **Explicit deep writes.** `set_path()` is required for nested creation, so a typo raises `AttributeError` instead of producing a phantom key — the silent failure mode of `addict`, `munch`, and `easydict`.
- **Path API with dot and array notation.** Expressions like `a.b.c` and `arr[0]` drive read, write, delete, and move operations.
- **Atomic batch updates.** `set_many()` applies every path or rolls them all back — no partial state on failure.
- **Change tracking.** `diff()` returns a precise list of adds, replaces, and deletes between two structures.
- **Zero dependencies, full dict compatibility, always-on security limits.** Standard library only, drop-in for the dict interface (`len`, `in`, `keys`, `values`, `items`, iteration, `to_dict()`), with built-in checks on nesting depth, array bounds, key format, value size, and circular references.

### How It Works

ZeroDict follows a single design principle: **reads are permissive, writes are strict**. Attribute and bracket access never raise on missing keys, returning a falsy sentinel instead. Deep writes go through an explicit `set_path()` call that accepts dot-and-bracket path expressions, so creating nested structure is always an intentional act. The same path grammar powers `get_path`, `delete_path`, `move`, `set_many`, and `diff`.

### When You Should Use It

- **Configuration management** — load JSON/YAML into a dict and access nested settings without defensive `.get()` chains; batch-update settings atomically.
- **API response processing** — read deeply nested fields without guarding every level for optional or missing keys.
- **Data transformation pipelines** — reshape nested structures with path-based set/get/delete/move and audit changes via `diff()`.
- **Prototyping and exploration** — build and manipulate nested data in notebooks or scripts without boilerplate.
- **Handling untrusted nested data** — rely on the always-on security limits to bound depth, array indexes, key format, and value size.

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

## Behavior in Detail

The "permissive reads, strict writes" principle plays out through three concrete mechanisms.

### The MissingPath sentinel

When you traverse a path that doesn't exist, ZeroDict returns a `MissingPath` object — not `None`, and not a freshly-created empty dict. It is falsy in boolean context, equal to `None` under `==`, and chainable, so deep traversal of a missing path never raises and never mutates the underlying data:

```python
config = ZeroDict({"db": {"host": "localhost"}})

config.cache              # MissingPath (no KeyError, no mutation)
config.cache.ttl.timeout  # Still MissingPath, still no mutation
bool(config.cache)        # False
config.cache == None      # True
config.cache is None      # False — MissingPath is its own type
```

The last line matters in practice: `is None` will not detect a missing path. Use `== None`, plain truthiness, or `"key" in zd` to distinguish a real `None` value from an absent key.

### Asymmetric attribute access

Attribute reads are permissive on any depth. Attribute writes are strict — they only succeed for keys that already exist at the target level, plus top-level key creation. Anything deeper requires `set_path()`:

```python
config = ZeroDict({"db": {"host": "localhost"}})

config.db.host = "remote"           # OK — db.host already exists
config.new_field = "value"          # OK — top-level key creation
config.databse.host = "localhost"   # AttributeError — 'databse' missing
```

This asymmetry is what eliminates the typo-into-phantom-key class of bugs that affects `addict`, `munch`, and `easydict`.

### A single path grammar

The same `a.b.c` and `arr[0]` expressions drive every nested operation: `get_path`, `set_path`, `delete_path`, `move`, `set_many`, and `diff`. Learn the grammar once and you have read, write, batch, and audit covered:

```python
config.set_path("servers[0].host", "prod-1")
config.get_path("servers[0].host")
config.delete_path("servers[0].host")
config.move("servers[0]", "archive.first_server")
```

The underlying storage is a plain dict — `to_dict()` returns it unmodified, and ZeroDict implements the standard dict interface in full, so it composes cleanly with code that expects a dict-like object.

---

## Capability Map

A quick lookup of what to reach for when you need it. Each capability is documented in full under [Core Features](#core-features) and the [API Reference](https://github.com/francescofavi/zerodict/blob/main/docs/API_REFERENCE.md).

| You want to… | Reach for | Where to read more |
|---|---|---|
| Read a nested field safely | attribute access or `get_path()` | [Safe Reading](#safe-reading-with-dot-notation) |
| Create deep structure intentionally | `set_path()` | [Path API](#path-api-for-deep-creation) |
| Address arrays in a path | `set_path("a[0].b", …)` | [Array Manipulation](#array-manipulation) |
| Apply many updates atomically | `set_many()` | [Atomic Batch Updates](#atomic-batch-updates) |
| Move or rename a subtree | `move()` | [Move/Rename Fields](#moverename-fields) |
| Compare two structures | `diff()` | [Change Tracking](#change-tracking) |
| Switch to exception-on-miss | `strict=True` | [Strict Mode](#strict-mode) |
| Round-trip JSON or plain dict | `to_json` / `to_dict` / `from_*` | [Serialization](#serialization) |
| Stop circular refs and oversized inputs | always-on security limits | [Known limits and open issues](#known-limits-and-open-issues) |

These primitives compose: `set_many()` is `set_path()` applied transactionally, `move()` is `delete_path` + `set_path` in one atomic step, and `diff()` produces results in the same path grammar that `set_path` consumes — so an audit trail can be replayed by feeding it back into `set_many()`.

---

## Use Cases in Practice

The introduction lists the target scenarios. Below is what each one looks like in code.

### Configuration management

Load a config file, read deep settings without `.get()` ladders, batch-update related settings atomically:

```python
import json
from zerodict import ZeroDict

config = ZeroDict.from_json(open("config.json").read())

host = config.database.host
timeout = config.get_path("api.timeout", default=30)

config.set_many({
    "cache.enabled": True,
    "cache.ttl": 3600,
    "logging.level": "INFO",
})
```

### API response processing

Deeply nested API payloads can have any field missing without crashing the consumer:

```python
import json
from zerodict import ZeroDict

response = ZeroDict(json.loads(http_body))

email = response.data.user.email                          # MissingPath if absent
city  = response.get_path("data.user.address.city",
                          default="unknown")
if response.data.user.email:
    notify(response.data.user.email)
```

### Data transformation pipelines

Reshape nested records with path operations and audit the result:

```python
record = ZeroDict(raw_record)

record.set_path("normalized.email", record.email.lower())
record.move("legacy_address", "normalized.address")
record.delete_path("internal.debug_flags")

audit = ZeroDict(raw_record).diff(record)   # before → after delta
```

### Prototyping and exploration

Build nested experimental data in a notebook without intermediate-dict boilerplate:

```python
runs = ZeroDict({})

runs.set_path("trials[0].params.lr", 1e-3)
runs.set_path("trials[0].metrics.accuracy", 0.91)
runs.set_path("trials[1].params.lr", 5e-4)
runs.set_path("trials[1].metrics.accuracy", 0.93)
```

### Untrusted nested data

The always-on limits (nesting depth, array index bounds, key format, value size, circular references) reject pathological inputs without extra code on your side:

```python
ZeroDict(untrusted_payload)   # rejected if any limit is exceeded
```

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

**Requirements:** Python 3.12+ | No external dependencies (standard library only)

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
uv run python examples/01_quickstart.py
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

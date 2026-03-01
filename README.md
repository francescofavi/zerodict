# ZeroDict

[![CI](https://github.com/francescofavi/zerodict/actions/workflows/ci.yml/badge.svg)](https://github.com/francescofavi/zerodict/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zerodict)](https://pypi.org/project/zerodict/)
[![Python versions](https://img.shields.io/pypi/pyversions/zerodict)](https://pypi.org/project/zerodict/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Safe, explicit, and powerful manipulation of nested dict structures in Python.**

ZeroDict is a dict wrapper that makes working with nested data structures safer and more convenient, without sacrificing explicitness or introducing surprising behavior.

---

## Why ZeroDict?

Working with nested dictionaries in Python is error-prone:

```python
# Standard dict - fragile and verbose
config = {"database": {"host": "localhost"}}

# This crashes
print(config["cache"]["ttl"])  # KeyError!

# So you write defensive code everywhere
print(config.get("cache", {}).get("ttl"))  # Ugly and tedious
```

ZeroDict solves this with a clear philosophy: **safe reads, explicit writes**.

```python
from zerodict import ZeroDict

config = ZeroDict({"database": {"host": "localhost"}})

# Safe reading - no crashes
print(config.cache.ttl)  # None-like sentinel (no KeyError!)

# Explicit deep writes
config.set_path("cache.ttl", 3600)  # Creates entire path
print(config.cache.ttl)  # 3600
```

---

## Design Philosophy

### 1. Safe Reads, No Side Effects

Reading missing paths never crashes and never modifies your data:

```python
ed = ZeroDict({"a": 1})

# All of these are safe
ed.missing                    # Returns None-like sentinel
ed.deeply.nested.missing      # Returns None-like sentinel
ed.get_path("x.y.z")         # Returns None

# No KeyError, no auto-creation, no surprises
```

### 2. Explicit Deep Writes

Creating nested structures requires explicit intent via the Path API:

```python
ed = ZeroDict({"user": {}})

# First-level writes work with dot notation
ed.new_key = "value"  # Simple and clear

# Deep writes require explicit set_path
ed.set_path("user.address.city", "NYC")  # Explicit intent
```

**Why?** This prevents typos from silently creating garbage data. If you write `config.databse.host = "..."` (typo!), you want an error, not a new key.

### 3. Atomic Operations

Multi-path updates are all-or-nothing:

```python
# Either all updates succeed, or none do (automatic rollback)
config.set_many({
    "db.host": "localhost",
    "db.port": 5432,
    "cache.ttl": 3600
})
```

### 4. Security by Default

Built-in protections against common attacks:

- Maximum nesting depth (100 levels, prevents stack overflow)
- Maximum array indices (10000, prevents memory exhaustion)
- Key validation (prevents path injection)
- Circular reference detection
- Size limits on values (10MB)

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

**vs addict/munch/easydict:** These libraries auto-create nested dicts on write, which is convenient but dangerous:

```python
from addict import Dict
d = Dict()
d.databse.host = "localhost"  # Typo! Creates 'databse' key silently
```

ZeroDict prevents this with explicit `set_path()`:

```python
ed = ZeroDict({})
ed.databse.host = "localhost"  # Error: 'databse' doesn't exist
ed.set_path("database.host", "localhost")  # Explicit and safe
```

**vs python-box:** Box is feature-rich but complex. ZeroDict is focused: safe access + path manipulation + atomic operations, with clear semantics and no magic.

**vs plain dicts:** ZeroDict adds safety, path API, and atomic operations while maintaining dict compatibility. No `dict.get(x, {}).get(y, {}).get(z)` chains needed.

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

## Use Cases

### Configuration Management

```python
config = ZeroDict.from_json(config_file)

# Safe access with defaults
db_host = config.get_path("database.host", "localhost")
cache_ttl = config.get_path("cache.ttl", 3600)

# Atomic configuration updates
config.set_many({
    "database.pool.min": 5,
    "database.pool.max": 20,
    "cache.enabled": True
})
```

### API Response Processing

```python
response = ZeroDict(api_response)

# Safe nested access (no crashes on missing fields)
user_name = response.data.user.profile.name
avatar_url = response.data.user.avatar.url

if response.data.error.code:
    handle_error(response.data.error.message)
```

---

## Security Features

- **Maximum nesting depth:** 100 levels (prevents stack overflow)
- **Maximum array index:** 10000 (prevents memory exhaustion)
- **Maximum key length:** 1000 characters
- **Maximum value size:** 10MB per value
- **Key validation:** Only `[a-zA-Z0-9_-]` allowed (prevents path injection)
- **Circular reference detection:** Prevents infinite loops
- **Type validation:** Enforces dict structure integrity

All limits are configurable in the source code constants.

---

## Development Setup

### 1. Install uv

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and install

```bash
git clone https://github.com/francescofavi/zerodict.git
cd zerodict
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

### 3. Run tests and examples

```bash
uv run pytest
uv run python examples/demo.py
```

> All commands (`uv sync`, `uv run`) work identically on Linux, macOS, and Windows.

### Troubleshooting pre-commit hooks

If committing from an IDE (PyCharm, VS Code, etc.) fails with `pre-commit not found`, the git hooks cannot locate the `pre-commit` executable. This typically happens because the IDE calls `git` outside the project virtualenv.

**Fix 1 — Reinstall hooks** (most common cause after cloning or moving the repo):
```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

**Fix 2 — Install pre-commit globally** so any IDE can find it:
```bash
pipx install pre-commit
# or
uv tool install pre-commit
```

**Fix 3 — Commit from terminal** with the venv active:
```bash
source .venv/bin/activate
git commit -m "feat: my change"
```

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Commit messages are validated automatically by a git hook and in CI.

```
feat: add flatten() method          # new feature (minor version bump)
fix: handle None in strict mode     # bug fix (patch version bump)
docs: update README examples        # documentation only
refactor: split helpers into modules # code restructuring
test: add edge cases for set_many   # tests only
chore: rename dev scripts           # maintenance
```

---

## Further Documentation

- **[Full API Reference](doc/API_REFERENCE.md)** - Detailed documentation of all public APIs, parameters, and advanced usage patterns

## Contributing

This repository is maintained as a personal portfolio project. Pull requests are generally not accepted, but exceptional contributions may be considered.

For bug reports and feature requests, please use [GitHub Issues](https://github.com/francescofavi/zerodict/issues).

## License

MIT License - Copyright (c) 2025 Francesco Favi

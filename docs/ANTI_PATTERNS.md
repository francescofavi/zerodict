# Anti-Patterns - ZeroDict

## Purpose

Documents common mistakes and misuses when working with ZeroDict, explaining why they are wrong and how to do it correctly.

## Scope

- **Included:** Incorrect usage patterns for ZeroDict and MissingPath that lead to bugs, silent data corruption, or unexpected behavior.
- **Excluded:** General Python anti-patterns unrelated to ZeroDict.

---

## Anti-Patterns

### 1. Using `is None` to check for missing paths

**Description:** Comparing a MissingPath result with `is None` instead of `== None` or a boolean check.

**Why wrong:** `MissingPath` is not `None` — it is a sentinel that *equals* `None` via `__eq__`, but is a distinct object. `is` checks identity, not equality.

**Correct approach:**

```python
ed = ZeroDict({"a": 1})

# Wrong
if ed.missing is None:    # False! MissingPath is not None
    print("missing")

# Correct
if ed.missing == None:    # True
    print("missing")

# Better: use boolean check or 'in'
if not ed.missing:        # True (MissingPath is falsy)
    print("missing")

if "missing" not in ed:   # True
    print("missing")
```

---

### 2. Writing deep paths with dot notation instead of `set_path`

**Description:** Attempting to create nested structures using chained dot assignment.

**Why wrong:** Dot notation on a non-existent intermediate path returns `MissingPath`, and assigning to a `MissingPath` attribute raises `AttributeError`. This is by design — it prevents typos from silently creating garbage keys.

**Correct approach:**

```python
ed = ZeroDict({})

# Wrong: raises AttributeError
ed.database.host = "localhost"

# Correct: use set_path for deep creation
ed.set_path("database.host", "localhost")
```

---

### 3. Ignoring atomicity — using multiple `set_path` calls instead of `set_many`

**Description:** Applying multiple related changes with individual `set_path` calls when they should succeed or fail together.

**Why wrong:** If the third `set_path` fails, the first two have already mutated the data. There is no rollback, leaving the structure in an inconsistent state.

**Correct approach:**

```python
config = ZeroDict({"balance": 1000})

# Wrong: partial failure leaves inconsistent state
config.set_path("balance", 900)
config.set_path("transactions[0].amount", -100)
config.set_path("invalid..path", "value")  # Fails here, balance already changed

# Correct: atomic — all succeed or all roll back
config.set_many({
    "balance": 900,
    "transactions[0].amount": -100,
    "audit.timestamp": "2025-01-01"
})
```

---

### 4. Using reserved characters in keys

**Description:** Using `.`, `[`, or `]` in dictionary keys.

**Why wrong:** These characters are reserved for the path API. A key containing `.` would be ambiguous: is `"user.name"` a single key or a path with two segments?

**Correct approach:**

```python
# Wrong: raises ValueError
ed = ZeroDict({"user.name": "Alice"})
ed = ZeroDict({"items[0]": "value"})

# Correct: use path API for nested structures
ed = ZeroDict({})
ed.set_path("user.name", "Alice")
ed.set_path("items[0]", "value")

# Or use flat keys without reserved characters
ed = ZeroDict({"user_name": "Alice"})
```

---

### 5. Assuming thread safety

**Description:** Sharing a ZeroDict instance across threads without synchronization.

**Why wrong:** ZeroDict is explicitly NOT thread-safe. Concurrent reads and writes can corrupt internal state.

**Correct approach:**

```python
import threading

shared = ZeroDict({})
lock = threading.RLock()

# Wrong: no synchronization
# Thread A: shared.set_path("counter", 1)
# Thread B: shared.set_path("counter", 2)

# Correct: use a lock
with lock:
    shared.set_path("counter", shared.get_path("counter", default=0) + 1)
```

---

### 6. Using `to_dict()` result as if it were still a ZeroDict

**Description:** Calling `to_dict()` and then using path API or dot notation on the result.

**Why wrong:** `to_dict()` returns a plain `dict`. It has no `get_path`, `set_path`, or safe dot notation.

**Correct approach:**

```python
ed = ZeroDict({"user": {"name": "Alice"}})
plain = ed.to_dict()

# Wrong: AttributeError — plain dict has no get_path
plain.get_path("user.name")

# Correct: use dict access on plain dicts
plain["user"]["name"]

# Or keep using ZeroDict if you need path features
ed.get_path("user.name")
```

---

### 7. Expecting `delete_path` on arrays to remove elements

**Description:** Using `delete_path` on an array index and expecting the element to be removed from the list.

**Why wrong:** `delete_path` on an array index sets the element to `None` — it does not remove it. This preserves array length and indices, which is the intended behavior to avoid shifting indices.

**Correct approach:**

```python
ed = ZeroDict({"items": ["a", "b", "c"]})

# This sets items[1] to None, NOT removes it
ed.delete_path("items[1]")
# Result: {"items": ["a", None, "c"]}

# If you need actual removal, convert to dict first
data = ed.to_dict()
del data["items"][1]
ed = ZeroDict(data)
# Result: {"items": ["a", "c"]}
```

---

### 8. Confusing `None` value with missing key

**Description:** Treating a key that exists with `None` value the same as a key that does not exist.

**Why wrong:** A key set to `None` is a valid entry. A missing key returns `MissingPath` via dot notation. Both are falsy and both `== None`, but they are semantically different.

**Correct approach:**

```python
ed = ZeroDict({"a": None})

# Both are falsy
bool(ed.a)        # False
bool(ed.missing)  # False

# Use 'in' to distinguish
"a" in ed         # True — key exists
"missing" in ed   # False — key does not exist

# Or use contains_key
ed.contains_key("a")       # True
ed.contains_key("missing") # False
```

# FUNCTIONAL ANALYSIS

## Purpose

Business / PM / PO view of ZeroDict: the problem it addresses, the solution it provides, who uses it, what it integrates with, and what is intentionally out of scope. No implementation details — those belong in `ARCHITECTURE.md` and the source.

## Scope

- **Included:** problem statement, solution overview, headline features (mapped to public API), workflows, stakeholders, integration points, out-of-scope items, success criteria, configuration knobs that affect business behavior.
- **Excluded:** code-level analysis (see `ARCHITECTURE.md`), exhaustive symbol catalog (see `API_REFERENCE.md`), per-component limit table (see `LIMITATIONS.md`).

---

## Problem addressed

Python applications routinely manipulate nested dictionary structures: configuration files, REST/JSON API responses, document store payloads, transformation pipelines. Three pain points recur:

1. **Reading is fragile.** A single missing key crashes the program with `KeyError`. The standard mitigation — chained `.get()` calls with `{}` defaults — is verbose and easy to get wrong.
2. **Writing is verbose.** Creating a deep path requires manually initializing every intermediate level, and silently overwrites a non-dict value if one is in the way.
3. **The popular alternatives are dangerous.** `addict`, `munch`, `easydict`, and similar libraries make reads safe but auto-create nested dicts on **any** attribute access, including writes. A single typo silently materializes a phantom key, and the bug only surfaces in production.

ZeroDict is the answer to "I want safe reads but I refuse to accept silent writes."

## Solution overview

ZeroDict wraps a `dict[str, Any]` and applies one design rule: **safe reads, explicit writes**.

- Reading a missing path never raises and never mutates the wrapped data — it returns a `MissingPath` sentinel that compares equal to `None`, is falsy, and chains.
- Writing a deep path requires an explicit `set_path()` call. Plain attribute assignment is only allowed on existing paths — typos surface as `AttributeError` instead of becoming new keys.

On top of that core rule, the library ships a small set of features that recur in every nested-dict workflow: atomic batch updates, atomic move/rename, structural diff for change tracking, and JSON serialization. Every input is validated against a fixed set of security limits — the library is designed to be safe to feed untrusted data into.

## Stakeholders

| Stakeholder | How they interact |
|---|---|
| Application developer | Imports the library, wraps dict-shaped data, uses dot/path access |
| Configuration consumer (e.g. CLI, service bootstrap code) | Reads validated nested settings |
| Data-pipeline developer | Reshapes API responses, uses `diff()` for change detection |
| Security reviewer | Validates that the library cannot be used as a DoS vector against the host process |

The library has **no end-user UI**. Every interaction is through a Python import.

## Integration points

ZeroDict does not talk to any external service. Integration is purely in-process:

- **Inbound:** Python `dict` objects from any source — JSON parsers, YAML parsers, env-var unflatteners, ORM rows, message-queue payloads.
- **Outbound:** Plain `dict` (`to_dict()`), JSON string (`to_json()`), or pickled `MissingPath` (round-trips to `None`).

There is no network I/O, no filesystem I/O, no clock dependency, no thread spawning, no subprocess. The library is synchronous and side-effect-free apart from mutating its own wrapped state.

---

## Headline features (mapped to public API)

### F1 — Safe path reads

Read any nested path without crashing. Missing paths return a `MissingPath` sentinel (falsy, `== None`).

- API: `__getattr__` (dot notation), `get_path(path, default=None, *, strict=False)`
- Strict mode (`strict=True`) opt-in: raise `KeyError` / `TypeError` / `IndexError` instead of returning the default — useful for validating required fields.

### F2 — Explicit deep writes

Create or update a value at any nested path with one call. Intermediate `ZeroDict` and `list` containers are materialized as needed; types incompatible with the next path step are overwritten with a `UserWarning`.

- API: `set_path(path, value, *, strict=False)`
- Strict mode rejects writes whose intermediate path doesn't already exist.

### F3 — Atomic batch updates

Apply a group of `(path, value)` pairs as a single transaction. If any pair fails (invalid path, depth limit, value-size limit, type conflict in strict mode), every successful write that came before it is rolled back.

- API: `set_many(updates, *, strict=False)`
- Memory cost is proportional to the touched paths, not to the total wrapped data size.

### F4 — Atomic move / rename

Move a subtree (a leaf or a nested container) from one path to another in a single, rollback-protected operation. Rejects moves where the destination is a syntactic descendant of the source (would create a cycle).

- API: `move(source_path, dest_path, *, strict=False)`

### F5 — Structural diff

Compute a flat list of `add` / `remove` / `replace` operations between two `ZeroDict` instances. Useful for change auditing, dry-run previews, and debugging unexpected mutations.

- API: `diff(other)`

### F6 — Strict-mode validation

Every path operation accepts a `strict` flag. Switching it on turns silent fallbacks into raised exceptions — useful when the application wants to enforce a schema.

- API: `strict=True` parameter on `get_path`, `set_path`, `delete_path`, `set_many`, `move`.

### F7 — Standard dict interface

Drop-in compatible with the dict surface most consumer code expects: `len`, `in`, `iter`, `keys`/`values`/`items`, `get`/`pop`/`update`/`clear`/`setdefault`, bracket access, equality with both `ZeroDict` and plain `dict`.

### F8 — JSON / dict round-trip

Convert to plain `dict` (`to_dict()`) or JSON (`to_json()`), and back (`from_dict()`, `from_json()`). The JSON path forwards `**kwargs` to `json.dumps`.

### F9 — Built-in security envelope

Every input is bounds-checked against a fixed set of limits: nesting depth (100), key length (1000 bytes), value size (10 MB), array index (10,000), path length (10,000 chars). Circular references are detected during construction, wrapping, serialization, and diff. Limits are not user-configurable in the current release.

---

## Workflows

### W1 — Safe read with fallback

**Trigger:** application reads a possibly-missing config field.

1. Application calls `zd.section.field` or `zd.get_path("section.field", default=...)`.
2. Library walks the path. Missing intermediate or terminal returns the sentinel / default.
3. Application proceeds without a guard.

**Outcome:** no crash, no mutation, no defensive `.get(...)` chain.

### W2 — Build a deep config in one place

**Trigger:** application bootstraps a complex configuration tree.

1. Application starts from `ZeroDict({})` or `ZeroDict({...})`.
2. Application calls `set_path` (or `set_many`) for each leaf.
3. Library creates the intermediate `ZeroDict` / `list` containers automatically.

**Outcome:** the wrapped structure matches the desired shape; partial-failure cases are handled by `set_many`'s rollback.

### W3 — Apply a batch of related changes atomically

**Trigger:** application has N related updates that must succeed or fail together.

1. Application packs them into a `dict[path, value]`.
2. Application calls `set_many`.
3. Library backs up each touched path and applies writes in order. On any failure, it restores the original values and re-raises.

**Outcome:** the wrapped structure is either fully updated or untouched. Inconsistent intermediate states are not exposed to the caller.

### W4 — Track changes between two states

**Trigger:** application needs an audit trail or wants to validate a candidate change before committing it.

1. Application keeps a "before" `ZeroDict` and produces an "after" `ZeroDict`.
2. Application calls `before.diff(after)`.
3. Library walks both trees in parallel and emits `add` / `remove` / `replace` operations.

**Outcome:** the application has a flat, path-tagged list of every change.

### W5 — Move or rename a subtree during migration

**Trigger:** application is reorganizing a configuration schema or archiving a record.

1. Application calls `zd.move("old.location", "new.location")`.
2. Library validates the move (cannot cycle, paths well-formed), then writes destination and removes source under one rollback umbrella.

**Outcome:** the subtree is at its new location; the old location is gone; on any failure the structure is restored.

### W6 — Persist or transmit

**Trigger:** application needs to save or send the wrapped data.

1. Application calls `to_dict()` (for storage layers expecting a plain dict) or `to_json()` (for HTTP / files / queues).
2. Library produces the unwrapped representation.

**Outcome:** the result is interoperable with anything that accepts plain dicts or JSON.

---

## Configuration with business impact

### CONF-1 — Strict mode

`strict=False` (default) is the permissive path: missing reads return defaults, writes create intermediates. `strict=True` is the schema-enforcement path: any deviation raises. Decision lives at the call site, not at the instance level — different fields can apply different policies.

### CONF-2 — Security limits

All limits are fixed at module-level constants in `validator.py` (`MAX_NESTING_DEPTH`, `MAX_KEY_LENGTH`, `MAX_VALUE_SIZE`, `MAX_ARRAY_INDEX`, `MAX_PATH_LENGTH`, `MAX_MISSING_PATH_DEPTH`). They are not exposed to the user as a public API. Adjusting them requires editing the source. This is a deliberate trade-off — predictable behavior across deployments — but it is a real limitation when the host application has its own legitimate need for higher caps.

### CONF-3 — Serialization formatting

`to_json` forwards `**kwargs` to `json.dumps`. The defaults (`indent=2`, `ensure_ascii=False`) are biased towards human readability; bandwidth-sensitive callers pass `indent=None`.

---

## Out of scope

The library does **not** provide:

- **Schema validation.** ZeroDict checks structural and security limits, not value types or business rules. Pair it with `pydantic`, `jsonschema`, or hand-written validators if you need those.
- **Async / await.** Every method is synchronous. There are no `aget_path` variants.
- **Thread safety.** Concurrent writers must serialize externally (e.g. `threading.RLock`).
- **Lazy / streaming I/O.** The whole structure must fit in memory.
- **Path expression grammar beyond `a.b.c[i]`.** No wildcards, no slicing, no predicates, no JSONPath.
- **Configurable limits.** The security caps are fixed.
- **Persistence layer.** No connection to disk, network, or any storage backend.

These exclusions are deliberate — they keep the library small, predictable, and audit-friendly.

---

## Success criteria

The library is doing its job when:

- A read on a missing path never crashes user code.
- A typo in an attribute write surfaces as an `AttributeError` immediately, not as a silent phantom key.
- A batch update either fully succeeds or fully rolls back, with no observable intermediate state.
- An untrusted dict cannot exhaust memory or stack via the library's surface.
- The full public API can be learned from the `README` plus `API_REFERENCE.md` without reading the source.

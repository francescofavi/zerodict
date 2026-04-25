# ALTERNATIVES

## Purpose

Document the libraries ZeroDict positions itself against and why they are not interchangeable. The README contains a feature-comparison table; this is the long-form rationale.

## Scope

- **Included:** alternatives explicitly referenced in the README, in user-facing docs, or in source comments — and the trade-offs that make them inappropriate substitutes for ZeroDict's specific design choice.
- **Excluded:** speculative alternatives not derivable from the codebase or docs, dropped feature ideas (those live in `BUG_REPORT.md` under "candidate enhancements"), and unrelated dict utilities.

---

## Alternatives derived from the README

The README's "Comparison with Other Libraries" table compares ZeroDict against four named libraries: **addict**, **python-box**, **munch**, **easydict**. The narrative below those bullets calls out the trade-off pattern shared by addict / munch / easydict (auto-creating dicts on write) and contrasts python-box's broader feature surface.

### addict

| Property | Stance |
|---|---|
| Safe reads | Yes |
| Explicit deep writes | **No** — assigning to any attribute creates the path silently. |
| Path API | No |
| Atomic batch updates | No |
| Move/rename | No |
| Diff | No |
| Security limits | No |
| Type hints | Partial |

**Why not interchangeable:** addict embraces auto-creation as a feature. ZeroDict treats it as the bug it solves. A typo on `cfg.databse.host = "x"` becomes a real key in addict; ZeroDict raises `AttributeError` at the first missing level.

**When addict is the right choice:** prototyping where every nested write is meant to materialize the structure, and typo risk is acceptable.

### python-box

| Property | Stance |
|---|---|
| Safe reads | Yes |
| Explicit deep writes | No (auto-create) |
| Path API | Yes (rich — wildcards, conversion, frozen variants) |
| Atomic batch updates | No |
| Move/rename | No |
| Diff | No |
| Security limits | No |
| Type hints | Partial |

**Why not interchangeable:** python-box is feature-rich (frozen, default, ordered, environment-bound variants) but follows the same auto-create-on-write principle as addict. Its API surface is also significantly larger.

**When python-box is the right choice:** when the application needs Box's specific extras (frozen boxes, env-var integration, YAML/HCL helpers) and is comfortable with auto-create writes.

### munch

| Property | Stance |
|---|---|
| Safe reads | Yes (via attribute access) |
| Explicit deep writes | No |
| Path API | No |
| Atomic batch updates | No |
| Move/rename | No |
| Diff | No |
| Security limits | No |
| Type hints | No |

**Why not interchangeable:** munch is the minimal "dict-with-attribute-access" library. It does not add any of the higher-level operations ZeroDict ships (path API, batch, diff, move). It is a strictly smaller surface.

**When munch is the right choice:** when all that's needed is `obj.key` instead of `obj["key"]`, with no other ergonomics.

### easydict

| Property | Stance |
|---|---|
| Safe reads | Yes |
| Explicit deep writes | No |
| Path API | No |
| Atomic batch updates | No |
| Move/rename | No |
| Diff | No |
| Security limits | No |
| Type hints | No |

**Why not interchangeable:** easydict is closest in spirit to munch (dict-with-attribute-access) and shares the same limitations. The README treats it as a member of the same category.

**When easydict is the right choice:** legacy compatibility — code that already imports `easydict.EasyDict` and does not need any feature beyond attribute access.

---

## Alternatives not in the README but worth noting for the maintainer

Strictly speaking, ZeroDict's position is "safe-read + explicit-write". A reviewer evaluating ZeroDict will likely also have considered:

- **`pydantic`** — resolves dict-shape ambiguity at a different layer (schema first, structure second). When the application has a known schema, `pydantic` is the better tool. ZeroDict targets the case where the schema is partial, evolving, or inherited from an upstream system.
- **`jsonschema`** — validates a dict against a JSON Schema document. Complementary to ZeroDict, not a replacement: validate with `jsonschema`, then wrap the validated dict in `ZeroDict` for ergonomic access.
- **`dotmap`** — same auto-create-on-write semantics as addict / munch, with extra accessors. Same trade-off, same conclusion.
- **`benedict`** — feature-rich (path utilities, IO helpers, transformations) but auto-creates on write. Closer in API breadth to python-box than to ZeroDict.
- **`xmltodict` / `dataclasses-json`** — different problem space (transform-and-bind), not relevant comparisons.

These are not in the README's comparison table because they would dilute the table's main message ("auto-create-on-write is the trade-off ZeroDict refuses"). They are listed here so the maintainer is not surprised when a user asks "why isn't `benedict` in the comparison?".

---

## Decision summary

ZeroDict is not the right answer when:

- The application needs a schema-first validator → use `pydantic` or `jsonschema`.
- The application is fine with auto-create-on-write and wants the largest API surface → use `python-box` or `benedict`.
- The application only needs attribute access on a single-level dict → use `munch` / `easydict` / `dotmap`.

ZeroDict is the right answer when **safe reads, explicit writes, and a small audit-friendly surface** is the goal — and the user is willing to call `set_path()` for deep writes in exchange for typo-safety.

"""Test suite for ZeroDict.

Organized by feature:
1. Basic Operations (dot notation, dict interface)
2. Path API (get, set, delete)
3. Array Support
4. Batch Operations (set_many)
5. Move Operations
6. Diff (change tracking)
7. Validation (keys, types)
8. Security Limits (depth, size, circular refs)
9. Strict Mode
10. Serialization (JSON, dict)
11. MissingPath Behavior
12. Regression Tests

Copyright (c) 2025 Francesco Favi
"""

import contextlib
import pickle
import warnings
from typing import Any

import pytest

from zerodict import ZeroDict
from zerodict.path_api import Token

# =============================================================================
# BASIC OPERATIONS
# =============================================================================


class TestDotNotation:
    """Test dot notation for reading and writing."""

    def test_read_existing_values(self) -> None:
        zd = ZeroDict({"database": {"host": "localhost", "port": 5432}})

        assert zd.database.host == "localhost"
        assert zd.database.port == 5432

    def test_read_missing_returns_missing_path(self) -> None:
        zd = ZeroDict({"a": 1})

        assert not zd.missing  # Falsy
        assert zd.missing is not None  # MissingPath, not None

    def test_write_existing_path(self) -> None:
        zd = ZeroDict({"user": {"name": "John"}})

        zd.user.name = "Jane"

        assert zd.user.name == "Jane"

    def test_write_new_top_level_key(self) -> None:
        zd = ZeroDict({})

        zd.new_field = "value"

        assert zd.new_field == "value"


class TestDictInterface:
    """Test standard dict operations."""

    def test_len_contains_getitem(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        assert len(zd) == 2
        assert "a" in zd
        assert zd["a"] == 1

    def test_setitem_delitem(self) -> None:
        zd = ZeroDict({"a": 1})

        zd["b"] = 2
        assert zd["b"] == 2

        del zd["b"]
        assert "b" not in zd

    def test_keys_values_items(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        assert "a" in zd
        assert 1 in zd.values()
        assert ("a", 1) in zd.items()

    def test_iter(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        assert list(zd) == ["a", "b"]

    def test_get_with_default(self) -> None:
        zd = ZeroDict({"a": 1})

        assert zd.get("a") == 1
        assert zd.get("missing", "default") == "default"

    def test_pop(self) -> None:
        zd = ZeroDict({"a": 1})

        value = zd.pop("a")

        assert value == 1
        assert "a" not in zd

    def test_update(self) -> None:
        zd = ZeroDict({"a": 1})

        zd.update({"b": 2, "c": 3})

        assert zd["b"] == 2
        assert zd["c"] == 3

    def test_clear(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        zd.clear()

        assert len(zd) == 0

    def test_setdefault(self) -> None:
        zd = ZeroDict({"a": 1})

        assert zd.setdefault("a", 99) == 1
        assert zd.setdefault("b", 2) == 2
        assert zd["b"] == 2

    def test_contains_key(self) -> None:
        zd = ZeroDict({"a": 1})

        assert zd.contains_key("a") is True
        assert zd.contains_key("missing") is False


class TestComparison:
    """Test equality comparison."""

    def test_compare_zerodicts(self) -> None:
        zd1 = ZeroDict({"a": 1, "b": 2})
        zd2 = ZeroDict({"a": 1, "b": 2})

        assert zd1 == zd2

    def test_compare_with_dict(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        assert zd == {"a": 1, "b": 2}
        assert zd != {"a": 999}

    def test_compare_nested_lists(self) -> None:
        zd1 = ZeroDict({"items": [{"id": 1}, {"id": 2}]})
        zd2 = ZeroDict({"items": [{"id": 1}, {"id": 2}]})
        zd3 = ZeroDict({"items": [{"id": 1}, {"id": 3}]})

        assert zd1 == zd2
        assert zd1 != zd3


class TestCopy:
    """Test copy operations."""

    def test_deep_copy_default(self) -> None:
        zd = ZeroDict({"nested": {"value": 1}})

        copied = zd.copy()
        copied.nested.value = 999

        assert zd.nested.value == 1  # Original unchanged

    def test_shallow_copy(self) -> None:
        zd = ZeroDict({"nested": {"value": 1}})

        shallow = zd.copy(deep=False)
        shallow.nested.value = 888

        assert zd.nested.value == 888  # Shared reference


# =============================================================================
# PATH API
# =============================================================================


class TestPathGet:
    """Test get_path operations."""

    def test_get_nested_value(self) -> None:
        zd = ZeroDict({"user": {"profile": {"name": "John"}}})

        assert zd.get_path("user.profile.name") == "John"

    def test_get_missing_returns_none(self) -> None:
        zd = ZeroDict({"a": 1})

        assert zd.get_path("missing.path") is None

    def test_get_with_default(self) -> None:
        zd = ZeroDict({})

        assert zd.get_path("missing", default="fallback") == "fallback"


class TestPathSet:
    """Test set_path operations."""

    def test_create_deep_structure(self) -> None:
        zd = ZeroDict({})

        zd.set_path("a.b.c.d", "deep")

        assert zd.get_path("a.b.c.d") == "deep"

    def test_overwrite_existing(self) -> None:
        zd = ZeroDict({"a": {"b": 1}})

        zd.set_path("a.b", 999)

        assert zd.get_path("a.b") == 999


class TestPathDelete:
    """Test delete_path operations."""

    def test_delete_nested_key(self) -> None:
        zd = ZeroDict({"a": {"b": 1, "c": 2}})

        zd.delete_path("a.b")

        assert zd.get_path("a.b") is None
        assert zd.get_path("a.c") == 2

    def test_delete_top_level_key(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        zd.delete_path("a")

        assert "a" not in zd


class TestPathValidation:
    """Test path validation."""

    def test_empty_path_rejected(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(ValueError, match="cannot be empty"):
            zd.get_path("")

    def test_leading_dot_rejected(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(ValueError, match="cannot start with a dot"):
            zd.get_path(".a.b")

    def test_trailing_dot_rejected(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(ValueError, match="cannot end with a dot"):
            zd.get_path("a.b.")

    def test_consecutive_dots_rejected(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(ValueError, match="consecutive dots"):
            zd.get_path("a..b")

    def test_invalid_key_in_path_rejected(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(ValueError, match="invalid character"):
            zd.set_path("bad key.value", 1)


# =============================================================================
# ARRAY SUPPORT
# =============================================================================


class TestArrayOperations:
    """Test array creation and access."""

    def test_create_array_elements(self) -> None:
        zd = ZeroDict({})

        zd.set_path("items[0].name", "First")
        zd.set_path("items[1].name", "Second")

        assert zd.get_path("items[0].name") == "First"
        assert zd.get_path("items[1].name") == "Second"

    def test_array_auto_extend(self) -> None:
        zd = ZeroDict({})

        zd.set_path("arr[5]", "value")

        assert zd.get_path("arr[5]") == "value"
        assert zd.get_path("arr[0]") is None  # Gap filled with None

    def test_nested_arrays(self) -> None:
        zd = ZeroDict({})

        zd.set_path("matrix[0][0]", "a")
        zd.set_path("matrix[0][1]", "b")

        assert zd.get_path("matrix[0][0]") == "a"
        assert zd.get_path("matrix[0][1]") == "b"
        assert isinstance(zd._data["matrix"], list)
        assert isinstance(zd._data["matrix"][0], list)

    def test_triple_nested_arrays(self) -> None:
        zd = ZeroDict({})

        zd.set_path("cube[0][0][0]", "deep")

        assert zd.get_path("cube[0][0][0]") == "deep"

    def test_modify_existing_nested_list(self) -> None:
        zd = ZeroDict({"matrix": [[1, 2], [3, 4]]})

        zd.set_path("matrix[0][1]", 99)

        assert zd.get_path("matrix[0][1]") == 99
        assert zd.get_path("matrix[1][0]") == 3  # Unchanged

    def test_delete_array_element_removes_it(self) -> None:
        zd = ZeroDict({"arr": [1, 2, 3]})

        zd.delete_path("arr[1]")

        assert zd._data["arr"] == [1, 3]  # Element actually removed
        assert len(zd._data["arr"]) == 2  # Length reduced

    def test_mixed_array_dict_path(self) -> None:
        zd = ZeroDict({})

        zd.set_path("users[0].tags[0]", "admin")

        assert zd.get_path("users[0].tags[0]") == "admin"
        assert isinstance(zd._data["users"], list)
        assert isinstance(zd._data["users"][0], ZeroDict)


# =============================================================================
# BATCH OPERATIONS
# =============================================================================


class TestSetMany:
    """Test atomic batch updates."""

    def test_multiple_updates(self) -> None:
        zd = ZeroDict({})

        zd.set_many({"a.b": 1, "c.d": 2, "e": 3})

        assert zd.get_path("a.b") == 1
        assert zd.get_path("c.d") == 2
        assert zd.get_path("e") == 3

    def test_rollback_on_error(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})
        deep_path = ".".join(["x"] * 200)  # Exceeds depth limit

        with contextlib.suppress(ValueError):
            zd.set_many({"a": 10, "b": 20, deep_path: "fail"})

        assert zd.get_path("a") == 1  # Rolled back
        assert zd.get_path("b") == 2

    def test_strict_mode_validates_paths(self) -> None:
        zd = ZeroDict({"a": {"b": 1}})

        with pytest.raises(KeyError):
            zd.set_many({"a.b": 10, "missing.path": 30}, strict=True)

        assert zd.get_path("a.b") == 1  # Rolled back

    def test_rollback_removes_created_paths(self) -> None:
        zd = ZeroDict({})
        deep_path = ".".join(["x"] * 200)

        with contextlib.suppress(ValueError):
            zd.set_many({"a.b": 1, deep_path: "fail"})

        assert zd.to_dict() == {}


# =============================================================================
# MOVE OPERATIONS
# =============================================================================


class TestMove:
    """Test move/rename operations."""

    def test_rename_within_parent(self) -> None:
        zd = ZeroDict({"section": {"old_name": "value"}})

        zd.move("section.old_name", "section.new_name")

        assert zd.get_path("section.new_name") == "value"
        assert zd.get_path("section.old_name") is None

    def test_move_to_different_location(self) -> None:
        zd = ZeroDict({"a": "value", "b": {}})

        zd.move("a", "b.a")

        assert zd.get_path("b.a") == "value"
        assert zd.get_path("a") is None

    def test_move_creates_intermediate_paths(self) -> None:
        zd = ZeroDict({"a": "value"})

        zd.move("a", "x.y.z")

        assert zd.get_path("x.y.z") == "value"

    def test_move_array_elements(self) -> None:
        zd = ZeroDict({"items": [1, 2, 3], "archived": []})

        zd.move("items[0]", "archived[0]")

        assert zd.get_path("archived[0]") == 1
        # After move, element is removed (not set to None), so items shifts
        assert zd._data["items"] == [2, 3]
        assert zd.get_path("items[0]") == 2

    def test_prevents_circular_reference(self) -> None:
        zd = ZeroDict({"a": {"b": {"c": "value"}}})

        with pytest.raises(ValueError, match="circular reference"):
            zd.move("a", "a.b.new")

    def test_validation_empty_paths(self) -> None:
        zd = ZeroDict({"a": 1})

        with pytest.raises(ValueError, match="cannot be empty"):
            zd.move("", "b")

    def test_validation_same_path(self) -> None:
        zd = ZeroDict({"a": 1})

        with pytest.raises(ValueError, match="cannot be the same"):
            zd.move("a", "a")

    def test_strict_source_must_exist(self) -> None:
        zd = ZeroDict({"a": 1})

        with pytest.raises(KeyError, match="does not exist"):
            zd.move("missing", "dest", strict=True)

    def test_strict_dest_must_not_exist(self) -> None:
        zd = ZeroDict({"a": 1, "b": 2})

        with pytest.raises(KeyError, match="already exists"):
            zd.move("a", "b", strict=True)

    def test_non_strict_overwrites_dest(self) -> None:
        zd = ZeroDict({"a": "new", "b": "old"})

        zd.move("a", "b", strict=False)

        assert zd.get_path("b") == "new"

    def test_non_strict_ignores_missing_source(self) -> None:
        zd = ZeroDict({"a": 1})

        zd.move("missing", "dest", strict=False)

        assert zd.to_dict() == {"a": 1}  # Unchanged

    def test_move_out_of_range_index(self) -> None:
        zd = ZeroDict({"arr": [1, 2]})

        zd.move("arr[10]", "dest", strict=False)
        assert zd.get_path("dest") is None

        with pytest.raises(KeyError, match="does not exist"):
            zd.move("arr[10]", "dest2", strict=True)


# =============================================================================
# DIFF
# =============================================================================


class TestDiff:
    """Test change tracking."""

    def test_basic_diff(self) -> None:
        zd1 = ZeroDict({"price": 100, "stock": 50})
        zd2 = ZeroDict({"price": 120, "stock": 45, "discount": 10})

        changes = zd1.diff(zd2)

        assert len(changes) > 0
        ops = [c["op"] for c in changes]
        assert "replace" in ops or "add" in ops

    def test_nested_diff(self) -> None:
        zd1 = ZeroDict({"a": {"b": {"c": 1}}})
        zd2 = ZeroDict({"a": {"b": {"c": 2}}})

        changes = zd1.diff(zd2)

        assert len(changes) == 1
        assert changes[0]["op"] == "replace"

    def test_diff_path_format(self) -> None:
        zd1 = ZeroDict({"items": [1, 2]})
        zd2 = ZeroDict({"items": [1, 3]})

        changes = zd1.diff(zd2)

        assert changes[0]["path"] == "items[1]"  # Not "items.[1]"


# =============================================================================
# VALIDATION
# =============================================================================


class TestKeyValidation:
    """Test key validation."""

    def test_valid_keys_accepted(self) -> None:
        zd = ZeroDict(
            {
                "username": "john",
                "user_name": "john",
                "user-name": "john",
                "user123": "john",
            }
        )

        assert len(zd) == 4

    def test_dot_in_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid character"):
            ZeroDict({"a.b": "value"})

    def test_bracket_in_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid character"):
            ZeroDict({"items[0]": "value"})

    def test_space_in_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid character"):
            ZeroDict({"my key": "value"})

    def test_empty_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            ZeroDict({"": "value"})

    def test_key_length_limit(self) -> None:
        huge_key = "a" * 10000

        with pytest.raises(ValueError, match="exceeds maximum"):
            ZeroDict({huge_key: "value"})


class TestTypeValidation:
    """Test input type validation."""

    def test_requires_dict(self) -> None:
        with pytest.raises(TypeError, match="requires a dict"):
            ZeroDict([1, 2, 3])  # type: ignore

        with pytest.raises(TypeError, match="requires a dict"):
            ZeroDict("string")  # type: ignore


class TestTokenValidation:
    """Test Token dataclass validation."""

    def test_valid_key_token(self) -> None:
        token = Token(key="a")
        assert token.key == "a"

    def test_valid_idx_token(self) -> None:
        token = Token(idx=0)
        assert token.idx == 0

    def test_neither_key_nor_idx_rejected(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            Token()

    def test_both_key_and_idx_rejected(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            Token(key="a", idx=0)


# =============================================================================
# SECURITY LIMITS
# =============================================================================


class TestSecurityLimits:
    """Test security limits."""

    def test_depth_limit(self) -> None:
        zd = ZeroDict({})
        deep_path = ".".join(["a"] * 200)

        with pytest.raises(ValueError, match="depth.*exceeds"):
            zd.set_path(deep_path, "value")

    def test_array_index_limit(self) -> None:
        zd = ZeroDict({})

        zd.set_path("arr[9999]", "ok")
        assert zd._data["arr"][9999] == "ok"

        with pytest.raises(IndexError, match="exceeds maximum"):
            zd.set_path("arr[10000]", "fail")

    def test_size_limit(self) -> None:
        huge_data = {f"key_{i}": "x" * 100000 for i in range(200)}

        with pytest.raises(ValueError, match="size.*exceeds"):
            ZeroDict(huge_data)

    def test_circular_reference_list(self) -> None:
        lst: list[Any] = []
        lst.append(lst)

        with pytest.raises(ValueError, match="Circular reference"):
            ZeroDict({"lst": lst})

    def test_circular_reference_dict(self) -> None:
        d: dict[str, Any] = {}
        d["self"] = d

        with pytest.raises(ValueError, match="Circular reference"):
            ZeroDict(d)

    def test_repr_truncates_large_dict(self) -> None:
        zd = ZeroDict({f"key{i}": i for i in range(200)})

        repr_str = repr(zd)

        assert "ZeroDict(" in repr_str
        assert len(repr_str) < 1000


# =============================================================================
# STRICT MODE
# =============================================================================


class TestStrictMode:
    """Test strict mode behavior."""

    def test_get_strict_raises_on_missing(self) -> None:
        zd = ZeroDict({"a": 1})

        with pytest.raises(KeyError):
            zd.get_path("missing", strict=True)

    def test_get_non_strict_returns_none(self) -> None:
        zd = ZeroDict({"a": 1})

        assert zd.get_path("missing") is None

    def test_get_strict_fails_on_none_traversal(self) -> None:
        zd = ZeroDict({"a": None})

        with pytest.raises(TypeError, match="Cannot traverse None"):
            zd.get_path("a.b.c", strict=True)


# =============================================================================
# SERIALIZATION
# =============================================================================


class TestSerialization:
    """Test JSON and dict serialization."""

    def test_to_dict(self) -> None:
        zd = ZeroDict({"a": {"b": 1}, "c": [1, 2]})

        plain = zd.to_dict()

        assert isinstance(plain, dict)
        assert not isinstance(plain, ZeroDict)
        assert plain == {"a": {"b": 1}, "c": [1, 2]}

    def test_from_dict(self) -> None:
        plain = {"a": {"b": 1}}

        zd = ZeroDict.from_dict(plain)

        assert isinstance(zd, ZeroDict)
        assert zd.get_path("a.b") == 1

    def test_to_json(self) -> None:
        zd = ZeroDict({"a": 1, "b": [1, 2]})

        json_str = zd.to_json()

        assert '"a"' in json_str
        assert '"b"' in json_str

    def test_from_json(self) -> None:
        json_str = '{"a": 1, "b": [1, 2]}'

        zd = ZeroDict.from_json(json_str)

        assert zd.get_path("a") == 1
        assert zd.get_path("b[0]") == 1

    def test_json_roundtrip(self) -> None:
        original = ZeroDict({"app": {"name": "Test", "debug": True}, "ports": [8000]})

        json_str = original.to_json()
        loaded = ZeroDict.from_json(json_str)

        assert loaded == original


# =============================================================================
# MISSING PATH BEHAVIOR
# =============================================================================


class TestMissingPath:
    """Test MissingPath sentinel behavior."""

    def test_is_falsy(self) -> None:
        zd = ZeroDict({})

        assert not zd.missing

    def test_equals_none(self) -> None:
        zd = ZeroDict({})

        assert zd.missing == None  # noqa: E711
        assert not (zd.missing != None)  # noqa: E711, SIM202

    def test_is_not_none(self) -> None:
        zd = ZeroDict({})

        assert zd.missing is not None

    def test_error_on_assignment(self) -> None:
        zd = ZeroDict({})

        with pytest.raises(AttributeError, match="Cannot set attribute"):
            zd.missing.deep.path = "value"

    def test_immutable(self) -> None:
        zd = ZeroDict({})
        missing = zd.nonexistent

        with pytest.raises(AttributeError):
            missing._path = "hacked"

    def test_pickle_returns_none(self) -> None:
        zd = ZeroDict({})
        missing = zd.missing

        pickled = pickle.dumps(missing)
        unpickled = pickle.loads(pickled)

        assert unpickled is None

    def test_hash_consistent_with_none(self) -> None:
        zd = ZeroDict({})
        missing = zd.missing

        mapping = {missing: "value"}

        assert mapping[None] == "value"
        assert len(mapping) == 1


# =============================================================================
# WARNINGS
# =============================================================================


class TestWarnings:
    """Test warning behavior."""

    def test_underscore_key_warning(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ZeroDict({"_internal": "value"})

            assert len(w) == 1
            assert "conflict" in str(w[0].message).lower()


# =============================================================================
# INTEGRATION
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_complex_workflow(self) -> None:
        zd = ZeroDict({})

        # Create structure
        zd.set_path("users[0].name", "Alice")
        zd.set_path("users[0].email", "alice@example.com")
        zd.set_path("users[1].name", "Bob")

        # Deep copy is independent
        copied = zd.copy()
        copied.set_path("users[0].name", "Changed")
        assert zd.get_path("users[0].name") == "Alice"

        # Delete path
        zd.delete_path("users[0].email")
        assert zd.get_path("users[0].email") is None

        # Batch update
        zd.set_many({"users[1].email": "bob@example.com", "config.debug": True})
        assert zd.get_path("users[1].email") == "bob@example.com"

    def test_deep_nesting(self) -> None:
        zd = ZeroDict({})

        zd.set_path("a.b.c.d.e.f.g.h.i.j", "deep")

        assert zd.get_path("a.b.c.d.e.f.g.h.i.j") == "deep"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

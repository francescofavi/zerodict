"""ZeroDict - Core class for convenient manipulation of nested dict structures."""

from __future__ import annotations

import copy
import warnings
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Any

from zerodict.diff_engine import DiffEngine
from zerodict.missing_path import MissingPath
from zerodict.path_api import PathAPI
from zerodict.serializer import Serializer
from zerodict.validator import MAX_NESTING_DEPTH, Validator

_MAX_REPR_LENGTH: int = 500


class ZeroDict:
    """
    Dict wrapper with path access. NOT thread-safe.

    Reading: zd.user.name or zd.get_path('user.name')
    Writing: zd.user.name = 'Jane' (existing path) or zd.set_path('a.b.c', 123) (creates path)
    Batch: zd.set_many({'x.y': 1, 'z': 2})
    Diff: zd.diff(other)

    Limits: depth=100, key_len=1000, value=10MB. Keys: [a-zA-Z0-9_-]

    Note: `zd == plain_dict` returns False on circular refs; `zd == other_zd` raises ValueError.
    """

    _data: dict[str, Any]

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        _visited: set[int] | None = None,
        _depth: int = 0,
    ) -> None:
        object.__setattr__(self, "_data", {})
        if _depth > MAX_NESTING_DEPTH:
            raise ValueError(
                f"Structure depth ({_depth}) exceeds maximum nesting depth ({MAX_NESTING_DEPTH})."
            )

        if data is not None:
            if not isinstance(data, dict):
                raise TypeError(
                    f"ZeroDict requires a dict, got {type(data).__name__}. "
                    f"Use ZeroDict({{'key': 'value'}}) to create from dict."
                )

            invalid_keys = [k for k in data if not isinstance(k, str)]
            if invalid_keys:
                raise TypeError(
                    f"All dict keys must be strings, found {len(invalid_keys)} non-string key(s): "
                    f"{invalid_keys[:3]}{'...' if len(invalid_keys) > 3 else ''}"
                )

            for k in data:
                Validator.validate_key(k)

            reserved_keys = [k for k in data if k.startswith("_")]
            if reserved_keys:
                warnings.warn(
                    f"Keys starting with '_' may conflict with internal attributes: {reserved_keys}. "
                    f"Access these keys using bracket notation: zd['{reserved_keys[0]}'] "
                    f"instead of zd.{reserved_keys[0]}",
                    UserWarning,
                    stacklevel=2,
                )

            Validator.validate_value_size(data)

            for k, v in data.items():
                self._data[k] = self._wrap(v, _visited, _depth + 1)

    def _wrap(self, v: Any, _visited: set[int] | None = None, _depth: int = 0) -> Any:
        if _visited is None:
            _visited = set()

        Validator.validate_value_size(v, _visited.copy())

        if isinstance(v, ZeroDict):
            v_depth = Validator.get_max_depth(v)
            if _depth + v_depth > MAX_NESTING_DEPTH:
                raise ValueError(
                    f"Structure depth ({_depth + v_depth}) exceeds maximum nesting depth ({MAX_NESTING_DEPTH})."
                )
            return v

        if isinstance(v, dict):
            obj_id = id(v)
            if obj_id in _visited:
                raise ValueError("Circular reference detected in input dict")
            _visited.add(obj_id)
            try:
                return ZeroDict(v, _visited, _depth)
            finally:
                _visited.discard(obj_id)

        if isinstance(v, list):
            list_id = id(v)
            if list_id in _visited:
                raise ValueError("Circular reference detected in input list")
            _visited.add(list_id)
            try:
                return [self._wrap(x, _visited, _depth + 1) for x in v]
            finally:
                _visited.discard(list_id)

        return v

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            return object.__getattribute__(self, key)
        if key in self._data:
            return self._data[key]
        return MissingPath(key)

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            Validator.validate_dict_key(key)
            self._data[key] = self._wrap(value)

    def get_path(self, path: str, default: Any = None, *, strict: bool = False) -> Any:
        return PathAPI.get(self, path, default, strict=strict)

    def set_path(self, path: str, value: Any, *, strict: bool = False) -> None:
        PathAPI.set(self, path, value, strict=strict)

    def delete_path(self, path: str, *, strict: bool = False) -> bool:
        return PathAPI.delete(self, path, strict=strict)

    def set_many(self, updates: dict[str, Any], *, strict: bool = False) -> None:
        PathAPI.set_many(self, updates, strict=strict)

    def move(self, source_path: str, dest_path: str, *, strict: bool = False) -> None:
        PathAPI.move(self, source_path, dest_path, strict=strict)

    def to_dict(self) -> dict[str, Any]:
        return Serializer.to_dict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ZeroDict:
        return ZeroDict(d)

    def to_json(self, **kwargs: Any) -> str:
        return Serializer.to_json(self, **kwargs)

    @staticmethod
    def from_json(s: str) -> ZeroDict:
        return Serializer.from_json(s)

    def diff(self, other: ZeroDict) -> list[dict[str, Any]]:
        return DiffEngine.diff(self, other)

    def __eq__(self, other: object) -> bool:
        return DiffEngine.compare(self, other)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        Validator.validate_dict_key(key, warn_underscore=True)
        self._data[key] = self._wrap(value)

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def keys(self) -> KeysView[str]:
        return self._data.keys()

    def items(self) -> ItemsView[str, Any]:
        return self._data.items()

    def values(self) -> ValuesView[Any]:
        return self._data.values()

    def get(self, key: str, default: Any = None) -> Any:
        Validator.validate_dict_key(key)
        return self._data.get(key, default)

    def pop(self, key: str, *args: Any) -> Any:
        Validator.validate_dict_key(key)
        return self._data.pop(key, *args)

    def update(self, other: dict[str, Any] | ZeroDict) -> None:
        items = list(other._data.items() if isinstance(other, ZeroDict) else other.items())
        # Validate all keys first to avoid partial state on validation failure
        for k, _ in items:
            Validator.validate_dict_key(k)
        # Only mutate state after all validations pass
        for k, v in items:
            self._data[k] = self._wrap(v)

    def clear(self) -> None:
        self._data.clear()

    def setdefault(self, key: str, default: Any = None) -> Any:
        Validator.validate_dict_key(key, warn_underscore=True)
        if key not in self._data:
            self._data[key] = self._wrap(default)
        return self._data[key]

    def contains_key(self, key: str) -> bool:
        return key in self._data

    def copy(self, deep: bool = True) -> ZeroDict:
        new_zd = ZeroDict.__new__(ZeroDict)
        if deep:
            try:
                object.__setattr__(new_zd, "_data", copy.deepcopy(self._data))
            except (TypeError, AttributeError) as e:
                raise TypeError(
                    f"Cannot deep copy ZeroDict: data contains non-serializable objects. "
                    f"Error: {e}. "
                    f"Use copy(deep=False) for shallow copy, or remove non-serializable objects."
                ) from e
            except Exception as e:
                raise TypeError(
                    f"Cannot deep copy ZeroDict: unexpected error during serialization. "
                    f"Error: {type(e).__name__}: {e}. "
                    f"Use copy(deep=False) for shallow copy."
                ) from e
        else:
            object.__setattr__(new_zd, "_data", self._data.copy())
        return new_zd

    def __repr__(self) -> str:
        try:
            repr_str = repr(self._data)
            if len(repr_str) > _MAX_REPR_LENGTH:
                shown_keys = repr_str[:_MAX_REPR_LENGTH].count("':")
                total_keys = len(self)
                return (
                    f"ZeroDict({repr_str[:_MAX_REPR_LENGTH]}... "
                    f"[showing ~{shown_keys} of {total_keys} keys])"
                )
            return f"ZeroDict({repr_str})"
        except RecursionError:
            return f"ZeroDict(<circular reference, {len(self)} keys>)"

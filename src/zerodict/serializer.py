"""Serialization utilities for ZeroDict."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from zerodict.validator import MAX_NESTING_DEPTH

if TYPE_CHECKING:
    from zerodict.zerodict import ZeroDict


class Serializer:
    """Serialization utilities for ZeroDict."""

    @staticmethod
    def _convert_value(v: Any, _visited: set[int], _depth: int) -> Any:
        from zerodict.zerodict import ZeroDict

        if _depth > MAX_NESTING_DEPTH:
            raise ValueError(f"Structure depth ({_depth}) exceeds maximum ({MAX_NESTING_DEPTH})")

        if isinstance(v, ZeroDict):
            return Serializer.to_dict(v, _visited, _depth + 1)
        if isinstance(v, list):
            list_id = id(v)
            if list_id in _visited:
                raise ValueError("Circular reference detected in list")
            _visited.add(list_id)
            try:
                return [Serializer._convert_value(x, _visited, _depth + 1) for x in v]
            finally:
                _visited.discard(list_id)
        return v

    @staticmethod
    def to_dict(zd: ZeroDict, _visited: set[int] | None = None, _depth: int = 0) -> dict[str, Any]:
        if _depth > MAX_NESTING_DEPTH:
            raise ValueError(f"Structure depth ({_depth}) exceeds maximum ({MAX_NESTING_DEPTH})")

        if _visited is None:
            _visited = set()

        obj_id = id(zd)
        if obj_id in _visited:
            raise ValueError("Circular reference detected")

        _visited.add(obj_id)
        try:
            out: dict[str, Any] = {}
            for k, v in zd._data.items():
                out[k] = Serializer._convert_value(v, _visited, _depth)
            return out
        finally:
            _visited.discard(obj_id)

    @staticmethod
    def to_json(zd: ZeroDict, **kwargs: Any) -> str:
        opts: dict[str, Any] = {"ensure_ascii": False, "indent": 2}
        opts.update(kwargs)
        return json.dumps(Serializer.to_dict(zd), **opts)

    @staticmethod
    def from_json(s: str) -> ZeroDict:
        from zerodict.zerodict import ZeroDict

        return ZeroDict(json.loads(s))

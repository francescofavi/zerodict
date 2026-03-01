"""Comparison and diff generation for ZeroDict."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from zerodict.serializer import Serializer
from zerodict.validator import MAX_NESTING_DEPTH

if TYPE_CHECKING:
    from zerodict.zerodict import ZeroDict


class DiffEngine:
    """Comparison and diff generation for ZeroDict."""

    @staticmethod
    def diff(zd1: ZeroDict, zd2: ZeroDict) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        visited: set[tuple[int, int]] = set()

        DiffEngine._walk_diff(a=zd1, b=zd2, changes=changes, visited=visited, prefix="", depth=0)
        return changes

    @staticmethod
    def _walk_diff(
        a: Any,
        b: Any,
        changes: list[dict[str, Any]],
        visited: set[tuple[int, int]],
        prefix: str = "",
        depth: int = 0,
    ) -> None:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        if depth > MAX_NESTING_DEPTH:
            raise ValueError(
                f"Diff depth ({depth}) exceeds maximum nesting depth ({MAX_NESTING_DEPTH}) "
                f"at path: {prefix}. Cannot diff - structures are too deeply nested."
            )

        # Convert plain dicts to ZeroDict for granular comparison
        if isinstance(a, dict) and not isinstance(a, ZeroDict):  # type: ignore[unreachable]
            a = ZeroDict(a)
        if isinstance(b, dict) and not isinstance(b, ZeroDict):  # type: ignore[unreachable]
            b = ZeroDict(b)

        if isinstance(a, ZeroDict) and isinstance(b, ZeroDict):
            pair_id = (id(a), id(b))
            if pair_id in visited:
                raise ValueError(f"Circular reference detected at path: {prefix}")
            visited.add(pair_id)
            try:
                akeys = set(a._data.keys())
                bkeys = set(b._data.keys())

                # Add dot separator if prefix ends with ] (coming from array)
                sep = "." if prefix.endswith("]") else ""

                for k in akeys - bkeys:
                    val = a._data[k]
                    if isinstance(val, ZeroDict):
                        val = Serializer.to_dict(val)
                    changes.append({"op": "remove", "path": f"{prefix}{sep}{k}", "before": val})

                for k in bkeys - akeys:
                    val = b._data[k]
                    if isinstance(val, ZeroDict):
                        val = Serializer.to_dict(val)
                    changes.append({"op": "add", "path": f"{prefix}{sep}{k}", "after": val})

                for k in akeys & bkeys:
                    DiffEngine._walk_diff(
                        a=a._data[k],
                        b=b._data[k],
                        changes=changes,
                        visited=visited,
                        prefix=f"{prefix}{sep}{k}.",
                        depth=depth + 1,
                    )
            finally:
                visited.discard(pair_id)

        elif isinstance(a, list) and isinstance(b, list):
            # Remove trailing dot before array index
            base_prefix = prefix[:-1] if prefix.endswith(".") else prefix
            minlen = min(len(a), len(b))
            for i in range(minlen):
                DiffEngine._walk_diff(
                    a=a[i],
                    b=b[i],
                    changes=changes,
                    visited=visited,
                    prefix=f"{base_prefix}[{i}]",
                    depth=depth + 1,
                )

            for i in range(minlen, len(a)):
                val = a[i]
                if isinstance(val, ZeroDict):
                    val = Serializer.to_dict(val)
                changes.append({"op": "remove", "path": f"{base_prefix}[{i}]", "before": val})

            for i in range(minlen, len(b)):
                val = b[i]
                if isinstance(val, ZeroDict):
                    val = Serializer.to_dict(val)
                changes.append({"op": "add", "path": f"{base_prefix}[{i}]", "after": val})

        else:
            # Import here to avoid circular dependency
            from zerodict.zerodict import ZeroDict

            aval = Serializer.to_dict(a) if isinstance(a, ZeroDict) else a
            bval = Serializer.to_dict(b) if isinstance(b, ZeroDict) else b

            try:
                are_equal = aval == bval
            except Exception as e:  # noqa: BLE001
                path = prefix[:-1] if prefix.endswith(".") else prefix
                warnings.warn(
                    f"Comparison failed at path '{path}': {type(e).__name__}: {e}. "
                    f"Treating values as not equal.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                are_equal = False

            if not are_equal:
                path = prefix[:-1] if prefix.endswith(".") else prefix
                changes.append({"op": "replace", "path": path, "before": aval, "after": bval})

    @staticmethod
    def compare(
        zd1: ZeroDict,
        other: object,
        _visited: set[tuple[int, int]] | None = None,
        _depth: int = 0,
    ) -> bool:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        if _depth > MAX_NESTING_DEPTH:
            raise ValueError(
                f"Comparison depth ({_depth}) exceeds maximum nesting depth ({MAX_NESTING_DEPTH}). "
                f"Cannot compare - structures are too deeply nested."
            )

        # Support comparison with plain dicts
        if isinstance(other, dict):
            try:
                return Serializer.to_dict(zd1) == other
            except ValueError:
                return False

        if not isinstance(other, ZeroDict):
            return False

        if _visited is None:
            _visited = set()

        pair_id = (id(zd1), id(other))
        if pair_id in _visited:
            return True

        _visited.add(pair_id)
        try:
            if set(zd1._data.keys()) != set(other._data.keys()):
                return False

            for key in zd1._data:
                val1 = zd1._data[key]
                val2 = other._data[key]

                if isinstance(val1, ZeroDict) and isinstance(val2, ZeroDict):
                    if not DiffEngine.compare(val1, val2, _visited, _depth + 1):
                        return False
                elif isinstance(val1, list) and isinstance(val2, list):
                    if not DiffEngine._compare_lists(val1, val2, _visited, _depth + 1):
                        return False
                else:
                    try:
                        if val1 != val2:
                            return False
                    except Exception as e:  # noqa: BLE001
                        warnings.warn(
                            f"Comparison failed for key '{key}': {type(e).__name__}: {e}. "
                            f"Treating values as not equal.",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                        return False

            return True
        finally:
            _visited.discard(pair_id)

    @staticmethod
    def _compare_lists(
        list1: list[Any],
        list2: list[Any],
        _visited: set[tuple[int, int]],
        _depth: int = 0,
    ) -> bool:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        if _depth > MAX_NESTING_DEPTH:
            raise ValueError(
                f"Comparison depth ({_depth}) exceeds maximum nesting depth ({MAX_NESTING_DEPTH}). "
                f"Cannot compare - structures are too deeply nested."
            )

        # Check for circular reference in lists
        list_pair_id = (id(list1), id(list2))
        if list_pair_id in _visited:
            return True  # Already compared this pair, consider equal
        _visited.add(list_pair_id)

        try:
            if len(list1) != len(list2):
                return False

            for i, item1 in enumerate(list1):
                item2 = list2[i]

                # Handle ZeroDict vs ZeroDict
                if isinstance(item1, ZeroDict) and isinstance(item2, ZeroDict):
                    if not DiffEngine.compare(item1, item2, _visited, _depth + 1):
                        return False
                # Handle mixed ZeroDict/dict (convert dict to ZeroDict for consistency)
                elif isinstance(item1, dict) and isinstance(item2, ZeroDict):
                    if not DiffEngine.compare(ZeroDict(item1), item2, _visited, _depth + 1):
                        return False
                elif isinstance(item1, ZeroDict) and isinstance(item2, dict):
                    if not DiffEngine.compare(item1, ZeroDict(item2), _visited, _depth + 1):
                        return False
                elif isinstance(item1, list) and isinstance(item2, list):
                    if not DiffEngine._compare_lists(item1, item2, _visited, _depth + 1):
                        return False
                else:
                    if item1 != item2:
                        return False

            return True
        finally:
            _visited.discard(list_pair_id)

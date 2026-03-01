"""MissingPath sentinel class for non-existent paths."""

from __future__ import annotations

import warnings
from typing import Any

from zerodict.validator import MAX_MISSING_PATH_DEPTH


def _unpickle_missing_path() -> None:
    """Unpickle helper - MissingPath becomes None when unpickled."""
    return None


class MissingPath:
    """
    Sentinel for non-existent paths. Behaves like None but provides clear errors.
    Use `== None` for comparisons (not `is None`). Hashable and JSON-serializable.
    """

    __slots__ = ("_path",)

    def __init__(self, path: str) -> None:
        object.__setattr__(self, "_path", path)

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        if other is None:
            return True
        if isinstance(other, MissingPath):
            return self._path == other._path
        return False

    def __repr__(self) -> str:
        return f"MissingPath({self._path!r})"

    def __str__(self) -> str:
        return "None"

    def __setattr__(self, key: str, value: Any) -> None:
        # MissingPath is immutable - only __init__ can set _path via object.__setattr__
        raise AttributeError(
            f"Cannot set attribute '{key}' on missing path '{self._path}'. "
            f"Path '{self._path}' does not exist. "
            f"Use set_path() to create deep paths, or ensure parent path exists first."
        )

    def __getattr__(self, key: str) -> MissingPath:
        new_path = f"{self._path}.{key}"
        depth = new_path.count(".") + 1

        if depth > MAX_MISSING_PATH_DEPTH:
            warnings.warn(
                f"MissingPath chain depth ({depth}) exceeds limit ({MAX_MISSING_PATH_DEPTH}). "
                f"This may indicate an infinite loop accessing non-existent nested attributes. "
                f"Path: '{new_path[:200]}...'",
                RuntimeWarning,
                stacklevel=2,
            )
        return MissingPath(new_path)

    def __hash__(self) -> int:
        # All MissingPath instances hash to hash(None) to maintain the hash/eq contract:
        # since MissingPath == None is True, hash(MissingPath) must equal hash(None).
        # This means {None}.add(MissingPath("x")) won't add the MissingPath (considered duplicate).
        # Different MissingPaths have same hash but __eq__ distinguishes them by path.
        return hash(None)

    def __reduce__(self) -> tuple[object, tuple[()]]:
        return (_unpickle_missing_path, ())

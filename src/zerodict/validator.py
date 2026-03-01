"""Centralized validation logic and security constants for ZeroDict."""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zerodict.path_api import Token

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_ARRAY_INDEX: int = 10000
MAX_NESTING_DEPTH: int = 100
MAX_KEY_LENGTH: int = 1000
MAX_VALUE_SIZE: int = 10_000_000
MAX_PATH_LENGTH: int = 10000
MAX_MISSING_PATH_DEPTH: int = 100

VALID_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_-]+$")

# =============================================================================
# VALIDATOR
# =============================================================================


class Validator:
    """Centralized validation logic for ZeroDict security."""

    @staticmethod
    def validate_key(key: str) -> None:
        if not key:
            raise ValueError("Key cannot be empty")

        if len(key) > MAX_KEY_LENGTH:
            raise ValueError(
                f"Key size {len(key)} bytes exceeds maximum {MAX_KEY_LENGTH}. Key: '{key[:50]}...'"
            )

        if not VALID_KEY_PATTERN.match(key):
            # Check for non-ASCII first (more specific error)
            non_ascii = [c for c in key if ord(c) > 127]
            if non_ascii:
                raise ValueError(
                    f"Key '{key}' contains non-ASCII character(s): {non_ascii}. "
                    f"Only ASCII letters, numbers, underscore, and hyphen are allowed."
                )
            # Otherwise, invalid ASCII chars
            invalid_chars = sorted(set(re.findall(r"[^a-zA-Z0-9_-]", key)))
            raise ValueError(
                f"Key '{key}' contains invalid character(s): {invalid_chars}. "
                f"Keys can only contain ASCII letters, numbers, underscore, and hyphen. "
                f"Reserved characters (. [ ]) are used by path API."
            )

    @staticmethod
    def get_max_depth(obj: Any, visited: set[int] | None = None) -> int:
        from zerodict.zerodict import ZeroDict

        if visited is None:
            visited = set()

        obj_id = id(obj)
        if obj_id in visited:
            return 0

        visited.add(obj_id)
        try:
            if isinstance(obj, ZeroDict):
                if not obj._data:
                    return 0
                return 1 + max(
                    (Validator.get_max_depth(v, visited) for v in obj._data.values()), default=0
                )
            if isinstance(obj, dict):
                if not obj:
                    return 0
                return 1 + max(
                    (Validator.get_max_depth(v, visited) for v in obj.values()), default=0
                )
            if isinstance(obj, list | tuple | set):
                if not obj:
                    return 0
                return 1 + max((Validator.get_max_depth(v, visited) for v in obj), default=0)
            return 0
        finally:
            visited.discard(obj_id)

    @staticmethod
    def estimate_size(obj: Any, visited: set[int] | None = None) -> int:
        if visited is None:
            visited = set()

        obj_id = id(obj)
        if obj_id in visited:
            return 0

        visited.add(obj_id)
        try:
            size = sys.getsizeof(obj)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    size += Validator.estimate_size(k, visited)
                    size += Validator.estimate_size(v, visited)
            elif isinstance(obj, list | tuple | set | frozenset):
                for item in obj:
                    size += Validator.estimate_size(item, visited)
            return size
        except RecursionError:
            raise ValueError(
                f"Structure is too deeply nested to estimate size (exceeds Python recursion limit). "
                f"Max allowed depth is {MAX_NESTING_DEPTH}."
            ) from None
        finally:
            visited.discard(obj_id)

    @staticmethod
    def validate_value_size(value: Any, visited: set[int] | None = None) -> None:
        estimated_size = Validator.estimate_size(value, visited)
        if estimated_size > MAX_VALUE_SIZE:
            raise ValueError(
                f"Value size ({estimated_size:,} bytes) exceeds maximum allowed "
                f"({MAX_VALUE_SIZE:,} bytes). Consider splitting into smaller structures."
            )

    @staticmethod
    def validate_path_depth(tokens: list[Token], path: str) -> None:
        if len(tokens) > MAX_NESTING_DEPTH:
            raise ValueError(
                f"Path depth {len(tokens)} exceeds maximum nesting depth {MAX_NESTING_DEPTH}. "
                f"Path: '{path[:100]}{'...' if len(path) > 100 else ''}'"
            )

    @staticmethod
    def validate_dict_key(key: Any, warn_underscore: bool = False) -> None:
        """Validate a key for dict operations (type check + format + underscore warning)."""
        import warnings

        if not isinstance(key, str):
            raise TypeError(f"Key must be a string, got {type(key).__name__}")
        Validator.validate_key(key)
        if warn_underscore and key.startswith("_"):
            warnings.warn(
                f"Key '{key}' starts with '_' and may conflict with internal attributes. "
                f"Access it using bracket notation: zd['{key}']",
                UserWarning,
                stacklevel=3,
            )

    @staticmethod
    def contains_circular_ref(obj: Any, target_id: int, visited: set[int] | None = None) -> bool:
        from zerodict.zerodict import ZeroDict

        if visited is None:
            visited = set()

        obj_id = id(obj)
        if obj_id in visited:
            return False
        if obj_id == target_id:
            return True

        visited.add(obj_id)
        try:
            if isinstance(obj, ZeroDict):
                for v in obj._data.values():
                    if Validator.contains_circular_ref(v, target_id, visited):
                        return True
            if isinstance(obj, dict):
                for v in obj.values():
                    if Validator.contains_circular_ref(v, target_id, visited):
                        return True
            if isinstance(obj, list | tuple | set | frozenset):
                for item in obj:
                    if Validator.contains_circular_ref(item, target_id, visited):
                        return True
            return False
        finally:
            visited.discard(obj_id)

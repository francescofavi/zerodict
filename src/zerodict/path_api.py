"""Path navigation and manipulation for ZeroDict."""

from __future__ import annotations

import contextlib
import copy
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from zerodict.missing_path import MissingPath
from zerodict.validator import MAX_ARRAY_INDEX, MAX_PATH_LENGTH, Validator

if TYPE_CHECKING:
    from zerodict.zerodict import ZeroDict


@dataclass(slots=True)
class Token:
    """Path component: either key (dict) or idx (array), not both."""

    key: str | None = None
    idx: int | None = None

    def __post_init__(self) -> None:
        if (self.key is None) == (self.idx is None):
            raise ValueError("Token must have exactly one of key or idx set, not both or neither")

        if self.key is not None and self.key == "":
            raise ValueError("Token key cannot be an empty string")

        if self.idx is not None and self.idx < 0:
            raise ValueError(f"Token index must be non-negative, got {self.idx}")


class PathAPI:
    """Path navigation and manipulation for ZeroDict."""

    @staticmethod
    def tokenize(path: str) -> list[Token]:
        if not path:
            raise ValueError("Path cannot be empty")

        if len(path) > MAX_PATH_LENGTH:
            raise ValueError(
                f"Path length ({len(path)} chars) exceeds maximum allowed ({MAX_PATH_LENGTH}). "
                f"Path preview: '{path[:100]}...'"
            )

        if path.startswith("."):
            raise ValueError("Path cannot start with a dot")
        if path.endswith("."):
            raise ValueError("Path cannot end with a dot")
        if ".." in path:
            raise ValueError("Path cannot contain consecutive dots")

        tokens: list[Token] = []
        i = 0
        current = ""

        while i < len(path):
            c = path[i]

            if c == ".":
                if current:
                    Validator.validate_key(current)
                    tokens.append(Token(key=current))
                    current = ""
                i += 1
                continue

            if c == "[":
                if current:
                    Validator.validate_key(current)
                    tokens.append(Token(key=current))
                    current = ""
                i += 1
                num = ""
                while i < len(path) and path[i] != "]":
                    if not path[i].isdigit():
                        raise ValueError(f"Non-numeric index at position {i}")
                    num += path[i]
                    i += 1
                if i >= len(path) or path[i] != "]":
                    raise ValueError("Missing closing bracket ]")
                if not num:
                    raise ValueError(f"Empty array index at position {i}")

                try:
                    idx = int(num)
                except ValueError as e:
                    raise ValueError(f"Invalid array index at position {i}: {e}") from e

                if idx < 0:
                    raise ValueError(f"Negative array index not allowed: {idx}")
                if idx >= MAX_ARRAY_INDEX:
                    raise IndexError(f"Array index {idx} exceeds maximum allowed {MAX_ARRAY_INDEX}")

                tokens.append(Token(idx=idx))
                i += 1
                continue

            current += c
            i += 1

        if current:
            Validator.validate_key(current)
            tokens.append(Token(key=current))

        return tokens

    @staticmethod
    def get(zd: ZeroDict, path: str, default: Any = None, *, strict: bool = False) -> Any:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        tokens = PathAPI.tokenize(path)
        Validator.validate_path_depth(tokens, path)

        cur: Any = zd

        for t in tokens:
            if t.key is not None:
                if not isinstance(cur, ZeroDict):
                    if strict:
                        raise TypeError("Cannot access key on non-dict node")
                    return default

                if t.key not in cur._data:
                    if strict:
                        raise KeyError(f"Key not found: {t.key}")
                    return default

                cur = cur._data[t.key]

                # If value is None and not at end of path, cannot traverse further
                if cur is None and t != tokens[-1]:
                    if strict:
                        raise TypeError(f"Cannot traverse None value at key '{t.key}'")
                    return default
            else:
                if not isinstance(cur, list):
                    if strict:
                        raise TypeError("Cannot access index on non-list node")
                    return default
                idx = t.idx if t.idx is not None else 0
                if idx < 0 or idx >= len(cur):
                    if strict:
                        raise IndexError(f"Index out of range: {idx}")
                    return default
                cur = cur[idx]

        return cur

    @staticmethod
    def set(zd: ZeroDict, path: str, value: Any, *, strict: bool = False) -> None:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        tokens = PathAPI.tokenize(path)
        Validator.validate_path_depth(tokens, path)

        cur: Any = zd

        for i, t in enumerate(tokens):
            is_last = i == len(tokens) - 1

            if t.key is not None:
                if not isinstance(cur, ZeroDict):
                    raise TypeError("Cannot set key on non-dict node")

                if is_last:
                    cur._data[t.key] = zd._wrap(value)
                else:
                    if t.key not in cur._data:
                        if strict:
                            raise KeyError(f"Intermediate key not found: {t.key}")
                        next_token = tokens[i + 1]
                        if next_token.idx is not None:
                            cur._data[t.key] = []
                        else:
                            cur._data[t.key] = ZeroDict()
                    else:
                        existing_value = cur._data[t.key]
                        next_token = tokens[i + 1]

                        if next_token.idx is not None:
                            if not isinstance(existing_value, list):
                                warnings.warn(
                                    f"Overwriting key '{t.key}' with incompatible type. "
                                    f"Existing: {type(existing_value).__name__}, Required: list. "
                                    f"Data will be lost: {existing_value!r}",
                                    UserWarning,
                                    stacklevel=4,
                                )
                                cur._data[t.key] = []
                        else:
                            if not isinstance(existing_value, ZeroDict):
                                warnings.warn(
                                    f"Overwriting key '{t.key}' with incompatible type. "
                                    f"Existing: {type(existing_value).__name__}, Required: ZeroDict. "
                                    f"Data will be lost: {existing_value!r}",
                                    UserWarning,
                                    stacklevel=4,
                                )
                                cur._data[t.key] = ZeroDict()
                    cur = cur._data[t.key]
            else:
                if not isinstance(cur, list):
                    raise TypeError("Cannot set index on non-list node")

                idx = t.idx if t.idx is not None else 0
                if idx < 0:
                    raise IndexError("Negative index not supported")
                if idx >= MAX_ARRAY_INDEX:
                    raise IndexError(f"Array index {idx} exceeds maximum allowed {MAX_ARRAY_INDEX}")

                if idx >= len(cur):
                    cur.extend([None] * (idx - len(cur) + 1))

                if is_last:
                    cur[idx] = zd._wrap(value)
                else:
                    existing_value = cur[idx]
                    next_token = tokens[i + 1]

                    # Handle navigation through existing lists (nested arrays)
                    if isinstance(existing_value, list):
                        if next_token.idx is None:
                            raise TypeError(
                                f"Cannot access key on list at index {idx}. "
                                f"Use array index notation [n] to access list elements."
                            )
                        cur = existing_value
                        continue

                    if existing_value is not None and not isinstance(existing_value, ZeroDict):
                        raise TypeError(
                            f"Cannot create nested path through non-dict value at index {idx}. "
                            f"Current value is {type(existing_value).__name__}: {existing_value!r}. "
                            f"This would overwrite the existing value. "
                            f"Delete the value first or use a different path."
                        )
                    if cur[idx] is None:
                        # Create list or ZeroDict based on next token type
                        if next_token.idx is not None:
                            cur[idx] = []
                        else:
                            cur[idx] = ZeroDict()
                    cur = cur[idx]

    @staticmethod
    def delete(zd: ZeroDict, path: str, *, strict: bool = False) -> bool:
        # Import here to avoid circular dependency
        from zerodict.zerodict import ZeroDict

        tokens = PathAPI.tokenize(path)
        Validator.validate_path_depth(tokens, path)

        cur: Any = zd

        for i, t in enumerate(tokens):
            is_last = i == len(tokens) - 1

            if t.key is not None:
                if not isinstance(cur, ZeroDict):
                    if strict:
                        raise TypeError("Cannot delete key on non-dict node")
                    return False

                if is_last:
                    if t.key in cur._data:
                        del cur._data[t.key]
                        return True
                    if strict:
                        raise KeyError(f"Key not found: {t.key}")
                    return False
                else:
                    if t.key not in cur._data:
                        if strict:
                            raise KeyError("Path not found")
                        return False
                    cur = cur._data[t.key]
            else:
                if not isinstance(cur, list):
                    if strict:
                        raise TypeError("Cannot delete index on non-list node")
                    return False

                idx = t.idx if t.idx is not None else 0
                if idx < 0 or idx >= len(cur):
                    if strict:
                        raise IndexError("Index out of range")
                    return False

                if is_last:
                    cur.pop(idx)
                    return True
                cur = cur[idx]

        return False

    @staticmethod
    def set_many(zd: ZeroDict, updates: dict[str, Any], *, strict: bool = False) -> None:
        if not updates:
            return

        rollback_info: list[tuple[str, Any, bool, str | None, bool | None]] = []

        try:
            for path, new_value in updates.items():
                tokens = PathAPI.tokenize(path)
                root_token = tokens[0]
                root_key = root_token.key
                root_existed = root_key in zd._data if root_key is not None else None

                try:
                    original_value_ref = PathAPI.get(zd, path, strict=True)
                    existed = True
                except (KeyError, TypeError, IndexError):
                    existed = False
                    original_value = None
                else:
                    # Separate deepcopy handling from path errors
                    try:
                        original_value = copy.deepcopy(original_value_ref)
                    except Exception:  # noqa: BLE001
                        original_value = original_value_ref  # Fallback for non-copyable

                rollback_info.append((path, original_value, existed, root_key, root_existed))
                PathAPI.set(zd, path, new_value, strict=strict)

        except Exception as e:
            rollback_errors: list[tuple[str, Exception]] = []
            for path, original_value, existed, root_key, root_existed in rollback_info:
                try:
                    if existed:
                        PathAPI.set(zd, path, original_value, strict=False)
                    else:
                        PathAPI.delete(zd, path, strict=False)
                        if root_key is not None and root_existed is False:
                            with contextlib.suppress(Exception):
                                del zd._data[root_key]
                except Exception as rollback_error:
                    rollback_errors.append((path, rollback_error))

            if rollback_errors:
                failed_paths = [path for path, _ in rollback_errors]
                warnings.warn(
                    f"set_many() rollback partially failed for {len(rollback_errors)} path(s): "
                    f"{failed_paths}. Data may be in inconsistent state. "
                    f"First rollback error: {rollback_errors[0][1]}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            raise e

    @staticmethod
    def move(zd: ZeroDict, source_path: str, dest_path: str, *, strict: bool = False) -> None:
        if not source_path or not source_path.strip():
            raise ValueError("Source path cannot be empty")
        if not dest_path or not dest_path.strip():
            raise ValueError("Destination path cannot be empty")
        if source_path == dest_path:
            raise ValueError("Source and destination paths cannot be the same")

        # Validate paths are syntactically correct
        PathAPI.tokenize(source_path)
        PathAPI.tokenize(dest_path)

        # Check for circular reference: dest cannot be child of source
        if dest_path.startswith(source_path + ".") or dest_path.startswith(source_path + "["):
            raise ValueError(
                f"Cannot move '{source_path}' to '{dest_path}': "
                f"destination is a child of source (would create circular reference)"
            )

        # Check if source exists (use MissingPath sentinel to distinguish from stored None)
        value = PathAPI.get(zd, source_path, default=MissingPath(source_path))
        is_missing = isinstance(value, MissingPath)
        if is_missing:
            if strict:
                raise KeyError(f"Source path '{source_path}' does not exist.")
            return

        # Check if destination exists (for strict mode)
        dest_value = PathAPI.get(zd, dest_path, default=MissingPath(dest_path))
        dest_exists = not isinstance(dest_value, MissingPath)
        if dest_exists and strict:
            raise KeyError(f"Destination path '{dest_path}' already exists.")

        # Atomic operation with rollback
        try:
            PathAPI.set(zd, dest_path, value, strict=False)
            PathAPI.delete(zd, source_path, strict=False)
        except Exception:
            # Rollback: restore original state
            if dest_exists:
                PathAPI.set(zd, dest_path, dest_value, strict=False)
            else:
                PathAPI.delete(zd, dest_path, strict=False)
            PathAPI.set(zd, source_path, value, strict=False)
            raise

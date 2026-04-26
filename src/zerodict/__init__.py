"""ZeroDict - Convenient manipulation of nested dict structures.

Features:
- Dot notation for reading (safe, no side effects)
- Dot notation for writing (only on existing paths)
- Path API for deep creation (a.b.c, array[0])
- Atomic batch updates
- Deep diff for change tracking

Copyright (c) 2025-present Francesco Favi
License: MIT
"""

from zerodict.missing_path import MissingPath
from zerodict.zerodict import ZeroDict

__version__ = "0.1.1"
__author__ = "Francesco Favi"
__email__ = "14098835+francescofavi@users.noreply.github.com"

__all__ = ["ZeroDict", "MissingPath"]

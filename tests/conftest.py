"""Shared fixtures for ZeroDict test suite."""

import pytest

from zerodict import ZeroDict


@pytest.fixture
def empty_zd() -> ZeroDict:
    """Return an empty ZeroDict instance."""
    return ZeroDict()


@pytest.fixture
def sample_zd() -> ZeroDict:
    """Return a populated ZeroDict instance."""
    return ZeroDict(
        {
            "user": {"name": "Alice", "age": 30},
            "settings": {"theme": "dark"},
        }
    )

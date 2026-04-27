"""Smoke-test all example scripts."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

scripts = [
    p for p in EXAMPLES_DIR.glob("*.py") if p.name != "__init__.py" and not p.name.startswith("_")
]


@pytest.mark.parametrize("script", scripts, ids=lambda p: p.name)
def test_example_runs(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"{script.name} failed:\n{result.stderr}"

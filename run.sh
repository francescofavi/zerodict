#!/usr/bin/env bash
set -euo pipefail

VENV=".venv"

# Ensure venv and dependencies are installed
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    uv sync
fi

echo "=========================================="
echo " Running tests"
echo "=========================================="
"$VENV/bin/python" -m pytest tests/ -v

echo ""
echo "=========================================="
echo " Running examples"
echo "=========================================="
"$VENV/bin/python" examples/demo.py

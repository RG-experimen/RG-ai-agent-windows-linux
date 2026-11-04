#!/usr/bin/env bash
# Launch script for Multi-Provider AI Agent (Linux / Kali / macOS)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "============================================================"
echo " Starting Multi-Provider AI Agent..."
echo "============================================================"

# Check if Python is available
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

$PY_CMD agent.py "$@"

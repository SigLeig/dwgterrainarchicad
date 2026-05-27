#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Could not find Python. Install Python 3.9 or newer first." >&2
  exit 1
fi

"$PYTHON_BIN" -m pip install --user -e .

echo
echo "Installed step-to-ifc for the current user."
echo "Test it with one of these commands:"
echo "  step-to-ifc --help"
echo "  ./step-to-ifc --help"
echo
echo "If 'step-to-ifc' is not found, add Python's user script folder to PATH."
echo "You still need FreeCAD installed for real STEP to IFC conversion."

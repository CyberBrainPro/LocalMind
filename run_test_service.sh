#!/bin/sh

# Ensure the script runs relative to the repo root.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

set -e

VENV_PATH="$SCRIPT_DIR/.venv/bin/activate"
if [ ! -f "$VENV_PATH" ]; then
  echo "Virtual environment not found at .venv. Please run 'python -m venv .venv' first."
  exit 1
fi

echo "Activating local virtual environment (.venv)..."
# shellcheck disable=SC1090
. "$VENV_PATH"

echo "Starting LocalMind test service on http://127.0.0.1:8787 ..."
uvicorn main:app --reload --port 8787

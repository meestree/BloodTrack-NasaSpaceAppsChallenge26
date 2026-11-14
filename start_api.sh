#!/usr/bin/env bash
# Start the local development API for Postman or a browser.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
API_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$API_PYTHON" ]]; then
    cat >&2 <<'SETUP'
The project virtual environment is missing. From the project folder, run:
  python3 -m venv .venv
  .venv/bin/python -m pip install -e '.[dev]'
Then run ./start_api.sh again.
SETUP
    exit 1
fi

cd -- "$PROJECT_DIR"
exec "$API_PYTHON" -m uvicorn backend.main:app \
    --app-dir "$PROJECT_DIR/src" \
    --host 127.0.0.1 \
    --port 8000 \
    "$@"

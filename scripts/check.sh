#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. See docs/LOCAL_BOOTSTRAP.md." >&2
  exit 1
fi

if [[ ! -f uv.lock ]]; then
  echo "uv.lock is missing. Run: uv lock && uv sync --locked" >&2
  exit 1
fi

uv sync --locked
uv run ruff check .
uv run pytest

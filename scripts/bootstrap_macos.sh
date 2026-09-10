#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap is intentionally macOS-only." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install uv from its official instructions, then rerun this script." >&2
  exit 1
fi

uv python install 3.14
uv lock
uv sync --locked
uv run ruff check .
uv run pytest

cat <<'EOF'
Bootstrap complete.
Next hardware step:
  uv run geoportlocal

Do not remove or overwrite the existing GeoPort application.
EOF

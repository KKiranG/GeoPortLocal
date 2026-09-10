#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "GeoPortLocal.app is currently qualified only from macOS." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. See docs/LOCAL_BOOTSTRAP.md." >&2
  exit 1
fi

if [[ ! -f uv.lock ]]; then
  echo "uv.lock is missing. Complete scripts/bootstrap_macos.sh first." >&2
  exit 1
fi

uv sync --locked
uv run ruff check .
uv run pytest
rm -rf build/GeoPortLocal dist/GeoPortLocal dist/GeoPortLocal.app
uv run pyinstaller --clean --noconfirm packaging/GeoPortLocal.spec

if [[ ! -d dist/GeoPortLocal.app ]]; then
  echo "PyInstaller completed without producing dist/GeoPortLocal.app." >&2
  exit 1
fi

echo "Built: $(pwd)/dist/GeoPortLocal.app"
echo "Do not replace the existing GeoPort.app during qualification."

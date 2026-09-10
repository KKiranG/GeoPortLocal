"""Command-line entry point for GeoPortLocal."""

from __future__ import annotations

import argparse

import uvicorn

from geoportlocal import __version__

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geoportlocal")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GeoPortLocal {__version__}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")

    uvicorn.run(
        "geoportlocal.app:app",
        host=DEFAULT_HOST,
        port=args.port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()

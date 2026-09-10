"""Command-line entry point for GeoPortLocal."""

from __future__ import annotations

import argparse
import logging
import socket
import threading
import webbrowser

import uvicorn

from geoportlocal import __version__
from geoportlocal.app import create_app
from geoportlocal.runtime.logging import configure_logging

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
_LOGGER = logging.getLogger("geoportlocal")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geoportlocal")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            f"Local HTTP port. If omitted, GeoPortLocal prefers {DEFAULT_PORT} and "
            "automatically chooses another loopback port when it is occupied."
        ),
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local server without opening the browser automatically.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GeoPortLocal {__version__}",
    )
    return parser


def bind_listener(
    requested_port: int | None,
    *,
    preferred_port: int = DEFAULT_PORT,
) -> socket.socket:
    """Atomically reserve a loopback listener without killing another process."""
    if requested_port is not None and not 1 <= requested_port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    if not 1 <= preferred_port <= 65535:
        raise ValueError("preferred_port must be between 1 and 65535")

    if requested_port is not None:
        try:
            return _listen_on(requested_port)
        except OSError as exc:
            raise SystemExit(
                f"Port {requested_port} is unavailable on {DEFAULT_HOST}; choose another --port."
            ) from exc

    try:
        return _listen_on(preferred_port)
    except OSError:
        return _listen_on(0)


def _listen_on(port: int) -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((DEFAULT_HOST, port))
        listener.listen(128)
    except Exception:
        listener.close()
        raise
    return listener


def _open_browser_later(url: str) -> None:
    timer = threading.Timer(0.45, webbrowser.open, args=(url,))
    timer.daemon = True
    timer.start()


def main() -> None:
    args = build_parser().parse_args()
    configure_logging()

    listener = bind_listener(args.port)
    actual_port = int(listener.getsockname()[1])
    url = f"http://{DEFAULT_HOST}:{actual_port}"

    if args.port is None and actual_port != DEFAULT_PORT:
        _LOGGER.warning(
            "Preferred port %s is occupied; using loopback port %s instead.",
            DEFAULT_PORT,
            actual_port,
        )
    _LOGGER.info("GeoPortLocal %s serving at %s", __version__, url)

    if not args.no_browser:
        _open_browser_later(url)

    config = uvicorn.Config(
        create_app,
        factory=True,
        host=DEFAULT_HOST,
        port=actual_port,
        reload=False,
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    try:
        server.run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()

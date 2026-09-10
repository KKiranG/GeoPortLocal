"""Browser-facing security policy for the loopback control plane."""

from __future__ import annotations

from urllib.parse import SplitResult, urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from geoportlocal.domain.errors import ErrorCode

_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "testserver"})
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "img-src 'self' https://tile.openstreetmap.org",
    )
)


def request_host_allowed(request: Request) -> bool:
    """Reject DNS-rebinding style Host values for the loopback-only app."""
    host = request.url.hostname
    return bool(host and host.casefold() in _ALLOWED_HOSTS)


def mutation_origin_allowed(request: Request) -> bool:
    """Allow local non-browser clients but require exact same-origin browser mutations."""
    if not request.url.path.startswith("/api/") or request.method not in _MUTATING_METHODS:
        return True

    if request.headers.get("sec-fetch-site", "").casefold() == "cross-site":
        return False

    origin = request.headers.get("origin")
    if not origin:
        # curl, local scripts and TestClient do not need to forge browser headers.
        return True

    try:
        parsed_origin = urlsplit(origin)
        request_host = request.url.hostname
        request_port = request.url.port
    except ValueError:
        return False

    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.hostname
        or not request_host
        or parsed_origin.hostname.casefold() not in _ALLOWED_HOSTS
        or request_host.casefold() not in _ALLOWED_HOSTS
    ):
        return False

    return (
        parsed_origin.scheme.casefold() == request.url.scheme.casefold()
        and parsed_origin.hostname.casefold() == request_host.casefold()
        and _effective_port(parsed_origin) == _effective_request_port(request.url.scheme, request_port)
    )


def _effective_port(url: SplitResult) -> int:
    if url.port is not None:
        return url.port
    return 443 if url.scheme.casefold() == "https" else 80


def _effective_request_port(scheme: str, port: int | None) -> int:
    if port is not None:
        return port
    return 443 if scheme.casefold() == "https" else 80


def rejected_request(message: str, *, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": message,
                "retryable": False,
            }
        },
    )


def apply_browser_security_headers(
    response: Response,
    *,
    no_store: bool = False,
) -> Response:
    response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if no_store:
        response.headers["Cache-Control"] = "no-store"
    return response

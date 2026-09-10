"""Browser-facing security policy for the loopback control plane."""

from __future__ import annotations

from urllib.parse import urlsplit

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
    host_header = request.headers.get("host", "")
    host = host_header.split(":", 1)[0].casefold()
    return host in _ALLOWED_HOSTS


def mutation_origin_allowed(request: Request) -> bool:
    """Allow local/non-browser API clients but reject browser cross-site mutation requests."""
    if not request.url.path.startswith("/api/") or request.method not in _MUTATING_METHODS:
        return True

    if request.headers.get("sec-fetch-site", "").casefold() == "cross-site":
        return False

    origin = request.headers.get("origin")
    if not origin:
        # curl, local scripts and TestClient do not need to forge browser headers.
        return True

    try:
        origin_host = urlsplit(origin).hostname
    except ValueError:
        return False
    return bool(origin_host and origin_host.casefold() in _ALLOWED_HOSTS)


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


def apply_browser_security_headers(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

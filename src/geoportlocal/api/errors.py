"""HTTP error handling for GeoPortLocal."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from geoportlocal.domain.errors import ErrorCode, GeoPortError

_LOGGER = logging.getLogger("geoportlocal.api")

_ERROR_STATUS = {
    ErrorCode.DEVICE_NOT_FOUND: 404,
    ErrorCode.DEVICE_METADATA_FAILED: 409,
    ErrorCode.DEVICE_NOT_TRUSTED: 409,
    ErrorCode.DEVELOPER_MODE_REQUIRED: 409,
    ErrorCode.IOS_VERSION_UNSUPPORTED: 422,
    ErrorCode.TUNNEL_UNAVAILABLE: 503,
    ErrorCode.DEVICE_DISCONNECTED: 409,
    ErrorCode.LOCATION_SET_FAILED: 502,
    ErrorCode.LOCATION_CLEAR_FAILED: 502,
    ErrorCode.OPERATION_TIMEOUT: 504,
    ErrorCode.FUEL_PROVIDER_UNAVAILABLE: 503,
    ErrorCode.FUEL_PROVIDER_INVALID_RESPONSE: 502,
    ErrorCode.INVALID_STATE: 409,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.INTERNAL_ERROR: 500,
}


def _error_response(error: GeoPortError) -> JSONResponse:
    return JSONResponse(
        status_code=_ERROR_STATUS.get(error.code, 500),
        content={
            "error": {
                "code": error.code.value,
                "message": error.message,
                "retryable": error.retryable,
            }
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(GeoPortError)
    async def handle_geoport_error(_: Request, error: GeoPortError) -> JSONResponse:
        return _error_response(error)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return _error_response(
            GeoPortError(
                ErrorCode.INVALID_REQUEST,
                "The request contains invalid or unsupported values.",
                retryable=False,
            )
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        # Do not serialize the exception or traceback to the browser. Normal logs
        # record only its class so an exception containing coordinates, identifiers
        # or dependency internals cannot become a routine diagnostic leak.
        _LOGGER.error("Unhandled application error type=%s", type(error).__name__)
        return _error_response(
            GeoPortError(
                ErrorCode.INTERNAL_ERROR,
                "GeoPortLocal encountered an unexpected internal error.",
                retryable=False,
            )
        )

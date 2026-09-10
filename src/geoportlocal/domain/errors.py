"""Stable application errors for GeoPortLocal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_METADATA_FAILED = "DEVICE_METADATA_FAILED"
    DEVICE_NOT_TRUSTED = "DEVICE_NOT_TRUSTED"
    DEVELOPER_MODE_REQUIRED = "DEVELOPER_MODE_REQUIRED"
    IOS_VERSION_UNSUPPORTED = "IOS_VERSION_UNSUPPORTED"
    TUNNEL_UNAVAILABLE = "TUNNEL_UNAVAILABLE"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    LOCATION_SET_FAILED = "LOCATION_SET_FAILED"
    LOCATION_CLEAR_FAILED = "LOCATION_CLEAR_FAILED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    FUEL_PROVIDER_UNAVAILABLE = "FUEL_PROVIDER_UNAVAILABLE"
    FUEL_PROVIDER_INVALID_RESPONSE = "FUEL_PROVIDER_INVALID_RESPONSE"
    INVALID_STATE = "INVALID_STATE"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    code: ErrorCode
    message: str
    retryable: bool


class GeoPortError(RuntimeError):
    """Expected application failure with a stable API-facing code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.cause = cause

    def as_info(self) -> ErrorInfo:
        return ErrorInfo(code=self.code, message=self.message, retryable=self.retryable)


class InvalidStateError(GeoPortError):
    def __init__(self, operation: str, state: str) -> None:
        super().__init__(
            ErrorCode.INVALID_STATE,
            f"Cannot {operation} while device state is '{state}'.",
            retryable=False,
        )

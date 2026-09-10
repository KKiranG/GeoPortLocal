"""Deterministic ownership of the active GeoPortLocal device session."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from geoportlocal.device.adapter import DeviceAdapter, DeviceConnection
from geoportlocal.domain.device import DeviceDescriptor, DeviceState, Location, SessionSnapshot
from geoportlocal.domain.errors import ErrorCode, GeoPortError, InvalidStateError
from geoportlocal.runtime.logging import redact_identifier

T = TypeVar("T")
PresenceProbe = Callable[[str], Awaitable[bool | None]]
_LOGGER = logging.getLogger("geoportlocal.device.session")

_TRANSPORT_FAILURES = {
    ErrorCode.DEVICE_DISCONNECTED,
    ErrorCode.TUNNEL_UNAVAILABLE,
    ErrorCode.OPERATION_TIMEOUT,
}


@dataclass(frozen=True, slots=True)
class SessionTimeouts:
    discovery: float = 5.0
    connect: float = 20.0
    set_location: float = 10.0
    clear_location: float = 10.0
    disconnect: float = 5.0
    presence: float = 2.0


class SessionManager:
    """Own exactly one live device connection and serialize all mutations."""

    def __init__(self, adapter: DeviceAdapter, *, timeouts: SessionTimeouts | None = None) -> None:
        self._adapter = adapter
        self._timeouts = timeouts or SessionTimeouts()
        self._operation_lock = asyncio.Lock()
        self._state = DeviceState.DISCONNECTED
        self._device: DeviceDescriptor | None = None
        self._connection: DeviceConnection | None = None
        self._location: Location | None = None
        self._last_error: GeoPortError | None = None

    @property
    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            state=self._state,
            device=self._device,
            location=self._location,
            last_error=self._last_error.as_info() if self._last_error else None,
        )

    async def discover(self) -> list[DeviceDescriptor]:
        async with self._operation_lock:
            started = time.perf_counter()
            connected_state = self._state if self._connection is not None else None
            if connected_state is None:
                self._state = DeviceState.DISCOVERING

            try:
                devices = await self._run(
                    self._adapter.discover(),
                    timeout=self._timeouts.discovery,
                    operation="discover devices",
                )
            except GeoPortError as error:
                self._last_error = error
                if connected_state is None:
                    self._state = DeviceState.DISCONNECTED
                _LOGGER.warning(
                    "device_discovery_failed code=%s duration_ms=%d",
                    error.code.value,
                    _elapsed_ms(started),
                )
                raise

            self._last_error = None
            if connected_state is None:
                self._state = DeviceState.DISCOVERED if devices else DeviceState.DISCONNECTED
            else:
                self._state = connected_state
            _LOGGER.info(
                "device_discovery_succeeded count=%d duration_ms=%d",
                len(devices),
                _elapsed_ms(started),
            )
            return devices

    async def connect(self, identifier: str) -> SessionSnapshot:
        if not identifier.strip():
            raise GeoPortError(
                ErrorCode.INVALID_REQUEST,
                "A device identifier is required.",
                retryable=False,
            )

        async with self._operation_lock:
            masked_identifier = redact_identifier(identifier)
            started = time.perf_counter()
            if self._connection is not None:
                if self._device and self._device.identifier == identifier and self._state in {
                    DeviceState.READY,
                    DeviceState.SIMULATING,
                }:
                    return self.snapshot
                raise InvalidStateError("connect another device", self._state.value)

            _LOGGER.info("connect_started device=%s", masked_identifier)
            self._state = DeviceState.CONNECTING
            self._device = None
            self._location = None

            try:
                connection = await self._run(
                    self._adapter.connect(identifier),
                    timeout=self._timeouts.connect,
                    operation="connect to device",
                )
            except GeoPortError as error:
                self._last_error = error
                self._state = DeviceState.DISCONNECTED
                _LOGGER.warning(
                    "connect_failed device=%s code=%s duration_ms=%d",
                    masked_identifier,
                    error.code.value,
                    _elapsed_ms(started),
                )
                raise

            if connection.descriptor.identifier != identifier:
                await self._close_quietly(connection)
                error = GeoPortError(
                    ErrorCode.INTERNAL_ERROR,
                    "The device adapter returned a connection for a different device.",
                )
                self._last_error = error
                self._state = DeviceState.DISCONNECTED
                _LOGGER.error(
                    "connect_failed device=%s code=%s duration_ms=%d",
                    masked_identifier,
                    error.code.value,
                    _elapsed_ms(started),
                )
                raise error

            self._connection = connection
            self._device = connection.descriptor
            self._last_error = None
            self._state = DeviceState.READY
            _LOGGER.info(
                "connect_succeeded device=%s duration_ms=%d",
                masked_identifier,
                _elapsed_ms(started),
            )
            return self.snapshot

    async def set_location(self, location: Location) -> SessionSnapshot:
        async with self._operation_lock:
            connection = self._require_connection("set location")
            if self._state not in {DeviceState.READY, DeviceState.SIMULATING}:
                raise InvalidStateError("set location", self._state.value)

            started = time.perf_counter()
            masked_identifier = redact_identifier(connection.descriptor.identifier)
            previous_state = self._state
            previous_location = self._location
            self._state = DeviceState.SETTING_LOCATION

            try:
                await self._run(
                    connection.set_location(location),
                    timeout=self._timeouts.set_location,
                    operation="set location",
                )
            except GeoPortError as error:
                if error.code in _TRANSPORT_FAILURES:
                    await self._invalidate(error)
                else:
                    self._state = previous_state
                    self._location = previous_location
                    self._last_error = error
                _LOGGER.warning(
                    "location_set_failed device=%s code=%s duration_ms=%d",
                    masked_identifier,
                    error.code.value,
                    _elapsed_ms(started),
                )
                raise

            self._location = location
            self._last_error = None
            self._state = DeviceState.SIMULATING
            _LOGGER.info(
                "location_set_succeeded device=%s duration_ms=%d",
                masked_identifier,
                _elapsed_ms(started),
            )
            return self.snapshot

    async def clear_location(self) -> SessionSnapshot:
        async with self._operation_lock:
            connection = self._require_connection("clear location")
            if self._state not in {DeviceState.READY, DeviceState.SIMULATING}:
                raise InvalidStateError("clear location", self._state.value)

            started = time.perf_counter()
            masked_identifier = redact_identifier(connection.descriptor.identifier)
            previous_state = self._state
            previous_location = self._location
            self._state = DeviceState.CLEARING

            try:
                await self._run(
                    connection.clear_location(),
                    timeout=self._timeouts.clear_location,
                    operation="clear location",
                )
            except GeoPortError as error:
                if error.code in _TRANSPORT_FAILURES:
                    await self._invalidate(error)
                else:
                    self._state = previous_state
                    self._location = previous_location
                    self._last_error = error
                _LOGGER.warning(
                    "location_clear_failed device=%s code=%s duration_ms=%d",
                    masked_identifier,
                    error.code.value,
                    _elapsed_ms(started),
                )
                raise

            self._location = None
            self._last_error = None
            self._state = DeviceState.READY
            _LOGGER.info(
                "location_clear_succeeded device=%s duration_ms=%d",
                masked_identifier,
                _elapsed_ms(started),
            )
            return self.snapshot

    async def disconnect(self) -> SessionSnapshot:
        async with self._operation_lock:
            connection = self._connection
            if connection is None:
                self._reset_local_state(preserve_error=False)
                return self.snapshot

            started = time.perf_counter()
            masked_identifier = redact_identifier(connection.descriptor.identifier)
            previous_state = self._state
            cleanup_error: GeoPortError | None = None
            self._state = DeviceState.DISCONNECTING

            if previous_state == DeviceState.SIMULATING:
                try:
                    await self._run(
                        connection.clear_location(),
                        timeout=self._timeouts.clear_location,
                        operation="clear location during disconnect",
                    )
                except GeoPortError as error:
                    cleanup_error = error

            try:
                await self._run(
                    connection.close(),
                    timeout=self._timeouts.disconnect,
                    operation="disconnect device",
                )
            except GeoPortError as error:
                cleanup_error = cleanup_error or error

            self._reset_local_state(preserve_error=True)
            self._last_error = cleanup_error
            log_method = _LOGGER.warning if cleanup_error else _LOGGER.info
            log_method(
                "disconnect_completed device=%s cleanup_code=%s duration_ms=%d",
                masked_identifier,
                cleanup_error.code.value if cleanup_error else "none",
                _elapsed_ms(started),
            )
            return self.snapshot

    async def check_presence(self, probe: PresenceProbe) -> SessionSnapshot:
        """Atomically invalidate a session only when a bounded probe proves physical absence."""
        async with self._operation_lock:
            if self._connection is None or self._device is None:
                return self.snapshot

            identifier = self._device.identifier
            try:
                present = await asyncio.wait_for(
                    probe(identifier),
                    timeout=self._timeouts.presence,
                )
            except Exception:
                # Presence is a liveness hint, not authority when the probe itself fails.
                return self.snapshot

            if present is not False:
                return self.snapshot

            started = time.perf_counter()
            masked_identifier = redact_identifier(identifier)
            error = GeoPortError(
                ErrorCode.DEVICE_DISCONNECTED,
                "The selected iOS device is no longer physically present.",
                retryable=True,
            )
            await self._invalidate(error)
            _LOGGER.warning(
                "device_absence_invalidated device=%s duration_ms=%d",
                masked_identifier,
                _elapsed_ms(started),
            )
            return self.snapshot

    async def shutdown(self) -> None:
        await self.disconnect()

    def _require_connection(self, operation: str) -> DeviceConnection:
        if self._connection is None:
            raise InvalidStateError(operation, self._state.value)
        return self._connection

    async def _invalidate(self, error: GeoPortError) -> None:
        connection = self._connection
        self._state = DeviceState.ERROR
        self._connection = None
        self._device = None
        self._location = None
        self._last_error = error

        if connection is not None:
            await self._close_quietly(connection)

        self._state = DeviceState.DISCONNECTED

    async def _close_quietly(self, connection: DeviceConnection) -> None:
        try:
            await asyncio.wait_for(connection.close(), timeout=self._timeouts.disconnect)
        except Exception:
            # Cleanup is best-effort here. The original operation error remains authoritative.
            pass

    def _reset_local_state(self, *, preserve_error: bool) -> None:
        previous_error = self._last_error if preserve_error else None
        self._connection = None
        self._device = None
        self._location = None
        self._state = DeviceState.DISCONNECTED
        self._last_error = previous_error

    async def _run(self, awaitable: Awaitable[T], *, timeout: float, operation: str) -> T:
        try:
            return await asyncio.wait_for(awaitable, timeout=timeout)
        except TimeoutError as exc:
            raise GeoPortError(
                ErrorCode.OPERATION_TIMEOUT,
                f"Timed out while attempting to {operation}.",
                retryable=True,
                cause=exc,
            ) from exc
        except GeoPortError:
            raise
        except Exception as exc:
            raise GeoPortError(
                ErrorCode.INTERNAL_ERROR,
                f"Unexpected failure while attempting to {operation}.",
                retryable=False,
                cause=exc,
            ) from exc


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))

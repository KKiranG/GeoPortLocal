"""Deterministic ownership of the active GeoPortLocal device session."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TypeVar

from geoportlocal.device.adapter import DeviceAdapter, DeviceConnection
from geoportlocal.domain.device import DeviceDescriptor, DeviceState, Location, SessionSnapshot
from geoportlocal.domain.errors import ErrorCode, GeoPortError, InvalidStateError

T = TypeVar("T")

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
                raise

            self._last_error = None
            if connected_state is None:
                self._state = DeviceState.DISCOVERED if devices else DeviceState.DISCONNECTED
            else:
                self._state = connected_state
            return devices

    async def connect(self, identifier: str) -> SessionSnapshot:
        if not identifier.strip():
            raise GeoPortError(
                ErrorCode.INVALID_REQUEST,
                "A device identifier is required.",
                retryable=False,
            )

        async with self._operation_lock:
            if self._connection is not None:
                if self._device and self._device.identifier == identifier and self._state in {
                    DeviceState.READY,
                    DeviceState.SIMULATING,
                }:
                    return self.snapshot
                raise InvalidStateError("connect another device", self._state.value)

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
                raise

            if connection.descriptor.identifier != identifier:
                await self._close_quietly(connection)
                error = GeoPortError(
                    ErrorCode.INTERNAL_ERROR,
                    "The device adapter returned a connection for a different device.",
                )
                self._last_error = error
                self._state = DeviceState.DISCONNECTED
                raise error

            self._connection = connection
            self._device = connection.descriptor
            self._last_error = None
            self._state = DeviceState.READY
            return self.snapshot

    async def set_location(self, location: Location) -> SessionSnapshot:
        async with self._operation_lock:
            connection = self._require_connection("set location")
            if self._state not in {DeviceState.READY, DeviceState.SIMULATING}:
                raise InvalidStateError("set location", self._state.value)

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
                raise

            self._location = location
            self._last_error = None
            self._state = DeviceState.SIMULATING
            return self.snapshot

    async def clear_location(self) -> SessionSnapshot:
        async with self._operation_lock:
            if self._state == DeviceState.READY and self._connection is not None:
                self._location = None
                self._last_error = None
                return self.snapshot

            connection = self._require_connection("clear location")
            if self._state != DeviceState.SIMULATING:
                raise InvalidStateError("clear location", self._state.value)

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
                    self._state = DeviceState.SIMULATING
                    self._location = previous_location
                    self._last_error = error
                raise

            self._location = None
            self._last_error = None
            self._state = DeviceState.READY
            return self.snapshot

    async def disconnect(self) -> SessionSnapshot:
        async with self._operation_lock:
            connection = self._connection
            if connection is None:
                self._reset_local_state(preserve_error=False)
                return self.snapshot

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

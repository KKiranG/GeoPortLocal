from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from geoportlocal.domain.device import ConnectionKind, DeviceDescriptor, Location
from geoportlocal.domain.errors import ErrorCode, GeoPortError


def make_descriptor() -> DeviceDescriptor:
    return DeviceDescriptor(
        identifier="00008150-TEST401C",
        name="iPhone",
        product_type="iPhone17,1",
        ios_version="26.5",
        connection=ConnectionKind.USB,
    )


@dataclass
class FakeConnection:
    descriptor: DeviceDescriptor
    set_error: GeoPortError | None = None
    clear_error: GeoPortError | None = None
    close_error: GeoPortError | None = None
    set_delay: float = 0.0
    set_started: asyncio.Event | None = None
    set_release: asyncio.Event | None = None
    set_calls: list[Location] = field(default_factory=list)
    clear_calls: int = 0
    close_calls: int = 0

    async def set_location(self, location: Location) -> None:
        self.set_calls.append(location)
        if self.set_started is not None:
            self.set_started.set()
        if self.set_release is not None:
            await self.set_release.wait()
        if self.set_delay:
            await asyncio.sleep(self.set_delay)
        if self.set_error:
            raise self.set_error

    async def clear_location(self) -> None:
        self.clear_calls += 1
        if self.clear_error:
            raise self.clear_error

    async def close(self) -> None:
        self.close_calls += 1
        if self.close_error:
            raise self.close_error


@dataclass
class FakeAdapter:
    descriptor: DeviceDescriptor
    connection: FakeConnection | None = None
    connect_error: GeoPortError | None = None
    discover_error: GeoPortError | None = None
    discover_calls: int = 0
    connect_calls: int = 0

    async def discover(self) -> list[DeviceDescriptor]:
        self.discover_calls += 1
        if self.discover_error:
            raise self.discover_error
        return [self.descriptor]

    async def connect(self, identifier: str) -> FakeConnection:
        self.connect_calls += 1
        if self.connect_error:
            raise self.connect_error
        if identifier != self.descriptor.identifier:
            raise GeoPortError(ErrorCode.DEVICE_NOT_FOUND, "Device not found.", retryable=True)
        if self.connection is None:
            self.connection = FakeConnection(self.descriptor)
        return self.connection

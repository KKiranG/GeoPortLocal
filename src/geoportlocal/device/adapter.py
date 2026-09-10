"""Project-owned boundary around the iOS device library."""

from __future__ import annotations

from typing import Protocol

from geoportlocal.domain.device import DeviceDescriptor, Location


class DeviceConnection(Protocol):
    @property
    def descriptor(self) -> DeviceDescriptor: ...

    async def set_location(self, location: Location) -> None: ...

    async def clear_location(self) -> None: ...

    async def close(self) -> None: ...


class DeviceAdapter(Protocol):
    async def discover(self) -> list[DeviceDescriptor]: ...

    async def connect(self, identifier: str) -> DeviceConnection: ...

"""Project-owned fuel-price provider boundary."""

from __future__ import annotations

from typing import Protocol

from geoportlocal.domain.fuel import FuelSnapshot


class FuelProvider(Protocol):
    async def fetch(self) -> FuelSnapshot: ...

    async def close(self) -> None: ...

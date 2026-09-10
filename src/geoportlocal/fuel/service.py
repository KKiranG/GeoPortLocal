"""Fuel-price application service with a small in-memory last-good cache."""

from __future__ import annotations

import asyncio

from geoportlocal.domain.errors import GeoPortError
from geoportlocal.domain.fuel import FuelQuote, FuelSnapshot
from geoportlocal.fuel.provider import FuelProvider


class FuelService:
    def __init__(self, provider: FuelProvider) -> None:
        self._provider = provider
        self._lock = asyncio.Lock()
        self._last_good: FuelSnapshot | None = None

    async def snapshot(self, *, allow_stale: bool = True) -> FuelSnapshot:
        async with self._lock:
            try:
                snapshot = await self._provider.fetch()
            except GeoPortError:
                if allow_stale and self._last_good is not None:
                    return self._last_good.as_stale()
                raise

            self._last_good = snapshot
            return snapshot

    async def regions(self) -> list[str]:
        snapshot = await self.snapshot()
        return sorted({quote.region for quote in snapshot.quotes})

    async def fuel_types(self, region: str) -> tuple[list[str], bool]:
        snapshot = await self.snapshot()
        normalized_region = region.casefold()
        fuel_types = sorted(
            {
                quote.fuel_type
                for quote in snapshot.quotes
                if quote.region.casefold() == normalized_region
            }
        )
        return fuel_types, snapshot.stale

    async def quote(self, region: str, fuel_type: str) -> FuelQuote | None:
        snapshot = await self.snapshot()
        normalized_region = region.casefold()
        normalized_type = fuel_type.casefold()
        return next(
            (
                quote
                for quote in snapshot.quotes
                if quote.region.casefold() == normalized_region
                and quote.fuel_type.casefold() == normalized_type
            ),
            None,
        )

    async def close(self) -> None:
        await self._provider.close()

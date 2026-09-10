"""Fuel-price domain models for GeoPortLocal."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class FuelQuote:
    region: str
    fuel_type: str
    price_cents_per_litre: float
    suburb: str | None
    state: str | None
    latitude: float
    longitude: float
    fetched_at: datetime
    stale: bool = False

    def __post_init__(self) -> None:
        if not self.region.strip():
            raise ValueError("Fuel region must not be empty.")
        if not self.fuel_type.strip():
            raise ValueError("Fuel type must not be empty.")
        if not math.isfinite(self.price_cents_per_litre) or self.price_cents_per_litre <= 0:
            raise ValueError("Fuel price must be a positive finite number.")
        if not math.isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("Fuel latitude must be a finite value between -90 and 90.")
        if not math.isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("Fuel longitude must be a finite value between -180 and 180.")
        if self.fetched_at.tzinfo is None:
            raise ValueError("Fuel fetch timestamp must be timezone-aware.")

    def as_stale(self) -> FuelQuote:
        return replace(self, stale=True)


@dataclass(frozen=True, slots=True)
class FuelSnapshot:
    quotes: tuple[FuelQuote, ...]
    fetched_at: datetime
    stale: bool = False

    @classmethod
    def current(cls, quotes: list[FuelQuote], fetched_at: datetime | None = None) -> FuelSnapshot:
        timestamp = fetched_at or datetime.now(UTC)
        return cls(quotes=tuple(quotes), fetched_at=timestamp, stale=False)

    def as_stale(self) -> FuelSnapshot:
        return FuelSnapshot(
            quotes=tuple(quote.as_stale() for quote in self.quotes),
            fetched_at=self.fetched_at,
            stale=True,
        )

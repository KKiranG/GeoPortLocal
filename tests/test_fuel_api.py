from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from geoportlocal.app import create_app
from geoportlocal.domain.errors import ErrorCode, GeoPortError
from geoportlocal.domain.fuel import FuelQuote, FuelSnapshot
from tests.fakes import FakeAdapter, make_descriptor


class FakeFuelProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.fetch_calls = 0
        self.close_calls = 0

    async def fetch(self) -> FuelSnapshot:
        self.fetch_calls += 1
        if self.fail:
            raise GeoPortError(
                ErrorCode.FUEL_PROVIDER_UNAVAILABLE,
                "Fuel provider unavailable.",
                retryable=True,
            )

        fetched_at = datetime(2026, 9, 10, 0, 0, tzinfo=UTC)
        return FuelSnapshot.current(
            [
                FuelQuote(
                    region="NSW",
                    fuel_type="U91",
                    price_cents_per_litre=169.9,
                    suburb="Hurstville",
                    state="NSW",
                    latitude=-33.9676,
                    longitude=151.1019,
                    fetched_at=fetched_at,
                )
            ],
            fetched_at=fetched_at,
        )

    async def close(self) -> None:
        self.close_calls += 1


def test_fuel_api_reuses_one_fresh_snapshot() -> None:
    fuel_provider = FakeFuelProvider()
    app = create_app(FakeAdapter(make_descriptor()), fuel_provider)

    with TestClient(app) as client:
        regions = client.get("/api/fuel/regions")
        types = client.get("/api/fuel/types", params={"region": "NSW"})
        quote = client.get("/api/fuel/quote", params={"region": "NSW", "type": "U91"})

        assert regions.status_code == 200
        assert regions.json() == {"regions": ["NSW"], "stale": False}
        assert types.status_code == 200
        assert types.json() == {"region": "NSW", "types": ["U91"], "stale": False}
        assert quote.status_code == 200
        assert quote.json()["quote"]["price"] == 169.9
        assert quote.json()["quote"]["stale"] is False
        assert fuel_provider.fetch_calls == 1

    assert fuel_provider.close_calls == 1


def test_fuel_outage_does_not_break_health_or_device_api() -> None:
    descriptor = make_descriptor()
    fuel_provider = FakeFuelProvider(fail=True)
    app = create_app(FakeAdapter(descriptor), fuel_provider)

    with TestClient(app) as client:
        fuel = client.get("/api/fuel/regions")
        health = client.get("/api/health")
        devices = client.get("/api/devices")
        connected = client.post("/api/device/connect", json={"identifier": descriptor.identifier})

        assert fuel.status_code == 503
        assert fuel.json()["error"]["code"] == "FUEL_PROVIDER_UNAVAILABLE"
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert devices.status_code == 200
        assert devices.json()["devices"][0]["identifier"] == descriptor.identifier
        assert connected.status_code == 200
        assert connected.json()["state"] == "ready"

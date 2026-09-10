from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from geoportlocal.domain.errors import ErrorCode, GeoPortError
from geoportlocal.domain.fuel import FuelQuote, FuelSnapshot
from geoportlocal.fuel.project_zero_three import PROJECT_ZERO_THREE_URL, ProjectZeroThreeProvider
from geoportlocal.fuel.service import FuelService


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "regions": [
            {
                "region": "NSW",
                "prices": [
                    {
                        "type": "U91",
                        "price": "169.9",
                        "suburb": "Hurstville",
                        "state": "NSW",
                        "lat": "-33.9676",
                        "lng": "151.1019",
                    },
                    {
                        "type": "U98",
                        "price": 189.9,
                        "suburb": "Hurstville",
                        "state": "NSW",
                        "lat": -33.9676,
                        "lng": 151.1019,
                    },
                ],
            }
        ]
    }


@pytest.mark.asyncio
async def test_project_zero_three_normalizes_expected_legacy_fields(
    valid_payload: dict[str, object],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == PROJECT_ZERO_THREE_URL
        return httpx.Response(200, json=valid_payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    snapshot = await provider.fetch()

    assert snapshot.stale is False
    assert len(snapshot.quotes) == 2
    quote = snapshot.quotes[0]
    assert quote.region == "NSW"
    assert quote.fuel_type == "U91"
    assert quote.price_cents_per_litre == 169.9
    assert quote.suburb == "Hurstville"
    assert quote.state == "NSW"
    assert quote.latitude == -33.9676
    assert quote.longitude == 151.1019
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_rejects_schema_change_instead_of_leaking_key_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"regions": [{"region": "NSW", "prices": [{"type": "U91"}]}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    with pytest.raises(GeoPortError) as raised:
        await provider.fetch()

    assert raised.value.code == ErrorCode.FUEL_PROVIDER_INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_rejects_malformed_json() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not-json")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    with pytest.raises(GeoPortError) as raised:
        await provider.fetch()

    assert raised.value.code == ErrorCode.FUEL_PROVIDER_INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_rejects_invalid_coordinates(valid_payload: dict[str, object]) -> None:
    payload = valid_payload.copy()
    regions = payload["regions"]
    assert isinstance(regions, list)
    region = regions[0]
    assert isinstance(region, dict)
    prices = region["prices"]
    assert isinstance(prices, list)
    price = prices[0]
    assert isinstance(price, dict)
    price["lat"] = 91

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    with pytest.raises(GeoPortError) as raised:
        await provider.fetch()

    assert raised.value.code == ErrorCode.FUEL_PROVIDER_INVALID_RESPONSE
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_retries_one_transport_failure(valid_payload: dict[str, object]) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200, json=valid_payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    snapshot = await provider.fetch()

    assert attempts == 2
    assert snapshot.quotes[0].fuel_type == "U91"
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_type", [httpx.ConnectTimeout, httpx.ReadTimeout])
async def test_provider_exhausts_bounded_transport_retry(failure_type) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise failure_type("timed out", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    with pytest.raises(GeoPortError) as raised:
        await provider.fetch()

    assert raised.value.code == ErrorCode.FUEL_PROVIDER_UNAVAILABLE
    assert raised.value.retryable is True
    assert attempts == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_retries_server_error_then_succeeds(
    valid_payload: dict[str, object],
) -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json=valid_payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    snapshot = await provider.fetch()

    assert attempts == 2
    assert snapshot.stale is False
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_does_not_retry_client_error() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(403, json={"error": "forbidden"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ProjectZeroThreeProvider(client)

    with pytest.raises(GeoPortError) as raised:
        await provider.fetch()

    assert raised.value.code == ErrorCode.FUEL_PROVIDER_UNAVAILABLE
    assert raised.value.retryable is False
    assert attempts == 1
    await client.aclose()


class FakeFuelProvider:
    def __init__(self, snapshot: FuelSnapshot) -> None:
        self.snapshot_value = snapshot
        self.error: GeoPortError | None = None
        self.fetch_calls = 0
        self.close_calls = 0

    async def fetch(self) -> FuelSnapshot:
        self.fetch_calls += 1
        if self.error:
            raise self.error
        return self.snapshot_value

    async def close(self) -> None:
        self.close_calls += 1


def make_snapshot() -> FuelSnapshot:
    fetched_at = datetime(2026, 9, 10, 0, 0, tzinfo=UTC)
    quote = FuelQuote(
        region="NSW",
        fuel_type="U91",
        price_cents_per_litre=169.9,
        suburb="Hurstville",
        state="NSW",
        latitude=-33.9676,
        longitude=151.1019,
        fetched_at=fetched_at,
    )
    return FuelSnapshot.current([quote], fetched_at=fetched_at)


@pytest.mark.asyncio
async def test_service_reuses_fresh_snapshot_for_ui_followup_calls() -> None:
    provider = FakeFuelProvider(make_snapshot())
    service = FuelService(provider, fresh_seconds=60)

    regions, regions_stale = await service.regions()
    fuel_types, types_stale = await service.fuel_types("NSW")
    quote = await service.quote("NSW", "U91")

    assert regions == ["NSW"]
    assert fuel_types == ["U91"]
    assert quote is not None and quote.price_cents_per_litre == 169.9
    assert regions_stale is False
    assert types_stale is False
    assert provider.fetch_calls == 1


@pytest.mark.asyncio
async def test_service_returns_none_for_unknown_fuel_type() -> None:
    provider = FakeFuelProvider(make_snapshot())
    service = FuelService(provider)

    quote = await service.quote("NSW", "NOT-A-TYPE")

    assert quote is None
    assert provider.fetch_calls == 1


@pytest.mark.asyncio
async def test_service_returns_explicitly_stale_last_good_data_after_outage() -> None:
    provider = FakeFuelProvider(make_snapshot())
    service = FuelService(provider, fresh_seconds=0)

    first = await service.snapshot()
    provider.error = GeoPortError(
        ErrorCode.FUEL_PROVIDER_UNAVAILABLE,
        "Provider unavailable.",
        retryable=True,
    )
    stale = await service.snapshot(force_refresh=True)

    assert first.stale is False
    assert stale.stale is True
    assert stale.quotes[0].stale is True
    assert provider.fetch_calls == 2

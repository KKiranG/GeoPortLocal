"""Project Zero Three fuel-price provider.

The provider is intentionally isolated because GeoPortLocal does not control the
upstream schema or availability. Device control never imports or depends on this
module.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from geoportlocal.domain.errors import ErrorCode, GeoPortError
from geoportlocal.domain.fuel import FuelQuote, FuelSnapshot

PROJECT_ZERO_THREE_URL = "https://projectzerothree.info/api.php?format=json"
_CONNECT_TIMEOUT = 3.0
_READ_TIMEOUT = 5.0
_RETRY_DELAY = 0.5
_MAX_ATTEMPTS = 2


class ProjectZeroThreeProvider:
    """Fetch and normalize the cheapest-price records exposed by Project Zero Three."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=_CONNECT_TIMEOUT,
                read=_READ_TIMEOUT,
                write=_READ_TIMEOUT,
                pool=_CONNECT_TIMEOUT,
            ),
            follow_redirects=True,
            headers={"User-Agent": "GeoPortLocal/0.1"},
        )

    async def fetch(self) -> FuelSnapshot:
        last_error: BaseException | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.get(PROJECT_ZERO_THREE_URL)
                if 500 <= response.status_code < 600:
                    raise _RetryableHttpError(response.status_code)
                response.raise_for_status()
                payload = response.json()
                return _parse_snapshot(payload)
            except (_RetryableHttpError, httpx.TransportError) as exc:
                last_error = exc
                if attempt + 1 < _MAX_ATTEMPTS:
                    await asyncio.sleep(_RETRY_DELAY)
                    continue
                raise _unavailable(exc) from exc
            except httpx.HTTPStatusError as exc:
                raise GeoPortError(
                    ErrorCode.FUEL_PROVIDER_UNAVAILABLE,
                    "The fuel-price provider rejected the request.",
                    retryable=False,
                    cause=exc,
                ) from exc
            except (ValueError, TypeError, KeyError) as exc:
                raise GeoPortError(
                    ErrorCode.FUEL_PROVIDER_INVALID_RESPONSE,
                    "The fuel-price provider returned an unexpected response.",
                    retryable=True,
                    cause=exc,
                ) from exc

        raise _unavailable(last_error)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class _RetryableHttpError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"upstream returned HTTP {status_code}")
        self.status_code = status_code


def _unavailable(cause: BaseException | None) -> GeoPortError:
    return GeoPortError(
        ErrorCode.FUEL_PROVIDER_UNAVAILABLE,
        "The fuel-price provider is temporarily unavailable.",
        retryable=True,
        cause=cause,
    )


def _parse_snapshot(payload: Any) -> FuelSnapshot:
    if not isinstance(payload, dict):
        raise TypeError("top-level response must be an object")

    regions = payload.get("regions")
    if not isinstance(regions, list) or not regions:
        raise ValueError("response must contain a non-empty regions list")

    fetched_at = datetime.now(UTC)
    quotes: list[FuelQuote] = []

    for region_record in regions:
        if not isinstance(region_record, dict):
            raise TypeError("region record must be an object")

        region = _required_string(region_record, "region")
        prices = region_record.get("prices")
        if not isinstance(prices, list):
            raise TypeError("region prices must be a list")

        for price_record in prices:
            if not isinstance(price_record, dict):
                raise TypeError("price record must be an object")

            quotes.append(
                FuelQuote(
                    region=region,
                    fuel_type=_required_string(price_record, "type"),
                    price_cents_per_litre=_required_float(price_record, "price"),
                    suburb=_optional_string(price_record.get("suburb")),
                    state=_optional_string(price_record.get("state")),
                    latitude=_required_float(price_record, "lat"),
                    longitude=_required_float(price_record, "lng"),
                    fetched_at=fetched_at,
                )
            )

    if not quotes:
        raise ValueError("response contained no fuel-price records")

    return FuelSnapshot.current(quotes, fetched_at=fetched_at)


def _required_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text field must be a string or null")
    stripped = value.strip()
    return stripped or None


def _required_float(record: dict[str, Any], key: str) -> float:
    value = record.get(key)
    if isinstance(value, bool):
        raise TypeError(f"{key} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{key} must be numeric") from exc

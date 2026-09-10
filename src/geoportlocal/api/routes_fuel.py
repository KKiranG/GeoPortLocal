"""Fuel-price routes for the local GeoPortLocal API."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from geoportlocal.domain.fuel import FuelQuote
from geoportlocal.fuel.service import FuelService

router = APIRouter(prefix="/api/fuel")


def _service(request: Request) -> FuelService:
    return request.app.state.fuel_service


def _quote_payload(quote: FuelQuote) -> dict[str, object]:
    return {
        "region": quote.region,
        "type": quote.fuel_type,
        "price": quote.price_cents_per_litre,
        "suburb": quote.suburb,
        "state": quote.state,
        "lat": quote.latitude,
        "lng": quote.longitude,
        "fetched_at": quote.fetched_at.isoformat(),
        "stale": quote.stale,
    }


@router.get("/regions")
async def regions(request: Request) -> dict[str, object]:
    values, stale = await _service(request).regions()
    return {"regions": values, "stale": stale}


@router.get("/types")
async def fuel_types(
    request: Request,
    region: str = Query(min_length=1, max_length=32),
) -> dict[str, object]:
    values, stale = await _service(request).fuel_types(region)
    return {"region": region, "types": values, "stale": stale}


@router.get("/quote")
async def fuel_quote(
    request: Request,
    region: str = Query(min_length=1, max_length=32),
    fuel_type: str = Query(alias="type", min_length=1, max_length=64),
) -> dict[str, object]:
    quote = await _service(request).quote(region, fuel_type)
    return {"quote": _quote_payload(quote) if quote else None}

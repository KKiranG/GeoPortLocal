"""Device and location routes for the local GeoPortLocal API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from geoportlocal.api.models import ConnectRequest, LocationRequest
from geoportlocal.api.serialization import device_payload, snapshot_payload
from geoportlocal.device.presence import PresenceProbe
from geoportlocal.device.session import SessionManager
from geoportlocal.domain.device import Location

router = APIRouter(prefix="/api")


def _manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def _presence_probe(request: Request) -> PresenceProbe | None:
    return getattr(request.app.state, "presence_probe", None)


@router.get("/devices")
async def list_devices(request: Request) -> dict[str, object]:
    devices = await _manager(request).discover()
    return {"devices": [device_payload(device) for device in devices]}


@router.post("/device/connect")
async def connect_device(request: Request, body: ConnectRequest) -> dict[str, object]:
    snapshot = await _manager(request).connect(body.identifier)
    return snapshot_payload(snapshot)


@router.get("/device/status")
async def device_status(request: Request) -> dict[str, object]:
    manager = _manager(request)
    probe = _presence_probe(request)
    snapshot = await manager.check_presence(probe) if probe is not None else manager.snapshot
    return snapshot_payload(snapshot)


@router.post("/location")
async def set_location(request: Request, body: LocationRequest) -> dict[str, object]:
    location = Location(latitude=body.latitude, longitude=body.longitude)
    snapshot = await _manager(request).set_location(location)
    return snapshot_payload(snapshot)


@router.delete("/location")
async def clear_location(request: Request) -> dict[str, object]:
    snapshot = await _manager(request).clear_location()
    return snapshot_payload(snapshot)


@router.post("/device/disconnect")
async def disconnect_device(request: Request) -> dict[str, object]:
    snapshot = await _manager(request).disconnect()
    return snapshot_payload(snapshot)

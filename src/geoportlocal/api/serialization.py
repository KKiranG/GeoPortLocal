"""Safe API serialization helpers."""

from __future__ import annotations

from geoportlocal.domain.device import DeviceDescriptor, Location, SessionSnapshot


def device_payload(device: DeviceDescriptor) -> dict[str, str | None]:
    return {
        "identifier": device.identifier,
        "name": device.name,
        "product_type": device.product_type,
        "ios_version": device.ios_version,
        "connection": device.connection.value,
    }


def location_payload(location: Location) -> dict[str, float]:
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
    }


def snapshot_payload(snapshot: SessionSnapshot) -> dict[str, object]:
    return {
        "state": snapshot.state.value,
        "device": device_payload(snapshot.device) if snapshot.device else None,
        "location": location_payload(snapshot.location) if snapshot.location else None,
        "last_error": (
            {
                "code": snapshot.last_error.code.value,
                "message": snapshot.last_error.message,
                "retryable": snapshot.last_error.retryable,
            }
            if snapshot.last_error
            else None
        ),
    }

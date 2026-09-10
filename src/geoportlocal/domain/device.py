"""Device-domain models for GeoPortLocal."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from geoportlocal.domain.errors import ErrorInfo


class ConnectionKind(StrEnum):
    USB = "usb"
    NETWORK = "network"
    UNKNOWN = "unknown"


class DeviceState(StrEnum):
    DISCONNECTED = "disconnected"
    DISCOVERING = "discovering"
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    READY = "ready"
    SETTING_LOCATION = "setting_location"
    SIMULATING = "simulating"
    CLEARING = "clearing"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DeviceDescriptor:
    identifier: str
    name: str | None = None
    product_type: str | None = None
    ios_version: str | None = None
    connection: ConnectionKind = ConnectionKind.UNKNOWN


@dataclass(frozen=True, slots=True)
class Location:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("Latitude and longitude must be finite numbers.")
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees.")


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    state: DeviceState
    device: DeviceDescriptor | None
    location: Location | None
    last_error: ErrorInfo | None

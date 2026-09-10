from __future__ import annotations

from dataclasses import dataclass

import pytest
from pymobiledevice3.exceptions import DvtException, MuxException, NotTrustedError

import geoportlocal.device.pymobiledevice as device_module
from geoportlocal.device.pymobiledevice import (
    PymobileDeviceAdapter,
    PymobileDeviceConnection,
    _connection_kind,
    _parse_ios_version,
    _require_modern_ios,
    _translate_exception,
)
from geoportlocal.domain.device import ConnectionKind, DeviceDescriptor, Location
from geoportlocal.domain.errors import ErrorCode, GeoPortError


@dataclass
class FakeMuxDevice:
    serial: str
    connection_type: str

    @property
    def is_usb(self) -> bool:
        return self.connection_type == "USB"


@pytest.mark.asyncio
async def test_discovery_deduplicates_network_and_usb_in_favour_of_usb(monkeypatch) -> None:
    identifier = "00008150-001D342A348A401C"

    async def list_devices():
        return [
            FakeMuxDevice(identifier, "Network"),
            FakeMuxDevice(identifier, "USB"),
        ]

    async def describe(selected_identifier: str, connection_type: str) -> DeviceDescriptor:
        return DeviceDescriptor(
            identifier=selected_identifier,
            ios_version="26.5",
            connection=_connection_kind(connection_type),
        )

    monkeypatch.setattr(device_module.usbmux, "list_devices", list_devices)
    adapter = PymobileDeviceAdapter()
    monkeypatch.setattr(adapter, "_describe", describe)

    devices = await adapter.discover()

    assert len(devices) == 1
    assert devices[0].identifier == identifier
    assert devices[0].connection == ConnectionKind.USB


@pytest.mark.asyncio
async def test_metadata_failure_preserves_discovered_device(monkeypatch) -> None:
    identifier = "00008150-001D342A348A401C"

    async def fail_metadata(**_):
        raise NotTrustedError()

    monkeypatch.setattr(device_module, "create_using_usbmux", fail_metadata)
    descriptor = await PymobileDeviceAdapter()._describe(identifier, "USB")

    assert descriptor.identifier == identifier
    assert descriptor.connection == ConnectionKind.USB
    assert descriptor.name is None
    assert descriptor.product_type is None
    assert descriptor.ios_version is None


def test_version_gate_accepts_modern_ios_and_rejects_legacy_path() -> None:
    assert _parse_ios_version("26.4.2") == (26, 4)
    _require_modern_ios(DeviceDescriptor(identifier="test", ios_version="17.4"))

    with pytest.raises(GeoPortError) as raised:
        _require_modern_ios(DeviceDescriptor(identifier="test", ios_version="17.3.1"))

    assert raised.value.code == ErrorCode.IOS_VERSION_UNSUPPORTED


def test_dependency_errors_translate_to_stable_project_errors() -> None:
    trust = _translate_exception(NotTrustedError(), operation="connect")
    tunnel = _translate_exception(MuxException(), operation="connect")
    location = _translate_exception(DvtException(), operation="set")

    assert trust.code == ErrorCode.DEVICE_NOT_TRUSTED
    assert tunnel.code == ErrorCode.TUNNEL_UNAVAILABLE
    assert location.code == ErrorCode.LOCATION_SET_FAILED


@pytest.mark.asyncio
async def test_tunnel_constructor_failure_returns_stable_error(monkeypatch) -> None:
    def fail_tunnel(**_):
        raise MuxException()

    monkeypatch.setattr(device_module, "PreferredRsdTunnel", fail_tunnel)
    descriptor = DeviceDescriptor(identifier="test", ios_version="26.5")

    with pytest.raises(GeoPortError) as raised:
        await PymobileDeviceConnection.open(descriptor)

    assert raised.value.code == ErrorCode.TUNNEL_UNAVAILABLE


@pytest.mark.asyncio
async def test_partial_location_context_failure_unwinds_entered_resources(monkeypatch) -> None:
    events: list[str] = []

    class AsyncContext:
        def __init__(self, name: str) -> None:
            self.name = name

        async def __aenter__(self):
            events.append(f"{self.name}.enter")
            return object()

        async def __aexit__(self, *_):
            events.append(f"{self.name}.exit")

    class FailingLocationContext:
        async def __aenter__(self):
            events.append("location.enter")
            raise DvtException("location service failed")

        async def __aexit__(self, *_):
            events.append("location.exit")

    monkeypatch.setattr(
        device_module,
        "PreferredRsdTunnel",
        lambda **_: AsyncContext("tunnel"),
    )
    monkeypatch.setattr(device_module, "DvtProvider", lambda _: AsyncContext("dvt"))
    monkeypatch.setattr(device_module, "LocationSimulation", lambda _: FailingLocationContext())

    descriptor = DeviceDescriptor(identifier="test", ios_version="26.5")
    with pytest.raises(GeoPortError) as raised:
        await PymobileDeviceConnection.open(descriptor)

    assert raised.value.code == ErrorCode.TUNNEL_UNAVAILABLE
    assert events == [
        "tunnel.enter",
        "dvt.enter",
        "location.enter",
        "dvt.exit",
        "tunnel.exit",
    ]


@pytest.mark.asyncio
async def test_connection_close_is_idempotent_and_set_failure_is_translated() -> None:
    class FakeStack:
        def __init__(self) -> None:
            self.close_calls = 0

        async def aclose(self) -> None:
            self.close_calls += 1

    class FailingLocation:
        async def set(self, *_: float) -> None:
            raise DvtException("set failed")

        async def clear(self) -> None:
            return None

    stack = FakeStack()
    descriptor = DeviceDescriptor(identifier="test", ios_version="26.5")
    connection = PymobileDeviceConnection(descriptor, stack, FailingLocation())  # type: ignore[arg-type]

    with pytest.raises(GeoPortError) as raised:
        await connection.set_location(Location(-33.8688, 151.2093))

    assert raised.value.code == ErrorCode.LOCATION_SET_FAILED

    await connection.close()
    await connection.close()
    assert stack.close_calls == 1


@pytest.mark.asyncio
async def test_clear_failure_is_translated_without_false_success() -> None:
    class FakeStack:
        async def aclose(self) -> None:
            return None

    class FailingLocation:
        async def set(self, *_: float) -> None:
            return None

        async def clear(self) -> None:
            raise DvtException("clear failed")

    descriptor = DeviceDescriptor(identifier="test", ios_version="26.5")
    connection = PymobileDeviceConnection(
        descriptor,
        FakeStack(),  # type: ignore[arg-type]
        FailingLocation(),  # type: ignore[arg-type]
    )

    with pytest.raises(GeoPortError) as raised:
        await connection.clear_location()

    assert raised.value.code == ErrorCode.LOCATION_CLEAR_FAILED
    await connection.close()

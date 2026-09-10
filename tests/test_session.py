from __future__ import annotations

import asyncio

import pytest

from geoportlocal.device.session import SessionManager, SessionTimeouts
from geoportlocal.domain.device import DeviceDescriptor, DeviceState, Location
from geoportlocal.domain.errors import ErrorCode, GeoPortError, InvalidStateError
from tests.fakes import FakeAdapter, FakeConnection, make_descriptor


@pytest.fixture
def descriptor() -> DeviceDescriptor:
    return make_descriptor()


@pytest.mark.asyncio
async def test_connect_does_not_cache_failed_session(descriptor: DeviceDescriptor) -> None:
    failure = GeoPortError(ErrorCode.TUNNEL_UNAVAILABLE, "Tunnel failed.", retryable=True)
    manager = SessionManager(FakeAdapter(descriptor, connect_error=failure))

    with pytest.raises(GeoPortError) as raised:
        await manager.connect(descriptor.identifier)

    assert raised.value.code == ErrorCode.TUNNEL_UNAVAILABLE
    assert manager.snapshot.state == DeviceState.DISCONNECTED
    assert manager.snapshot.device is None


@pytest.mark.asyncio
async def test_set_location_returns_only_after_real_success(descriptor: DeviceDescriptor) -> None:
    connection = FakeConnection(descriptor)
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))
    location = Location(latitude=-33.8688, longitude=151.2093)

    await manager.connect(descriptor.identifier)
    result = await manager.set_location(location)

    assert result.state == DeviceState.SIMULATING
    assert result.location == location
    assert connection.set_calls == [location]


@pytest.mark.asyncio
async def test_non_transport_set_failure_never_reports_simulating(
    descriptor: DeviceDescriptor,
) -> None:
    connection = FakeConnection(
        descriptor,
        set_error=GeoPortError(ErrorCode.LOCATION_SET_FAILED, "Set failed."),
    )
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))

    await manager.connect(descriptor.identifier)

    with pytest.raises(GeoPortError) as raised:
        await manager.set_location(Location(-33.8688, 151.2093))

    assert raised.value.code == ErrorCode.LOCATION_SET_FAILED
    assert manager.snapshot.state == DeviceState.READY
    assert manager.snapshot.location is None
    assert manager.snapshot.last_error is not None


@pytest.mark.asyncio
async def test_transport_failure_invalidates_connection(descriptor: DeviceDescriptor) -> None:
    connection = FakeConnection(
        descriptor,
        set_error=GeoPortError(
            ErrorCode.DEVICE_DISCONNECTED,
            "Device disconnected.",
            retryable=True,
        ),
    )
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))

    await manager.connect(descriptor.identifier)

    with pytest.raises(GeoPortError):
        await manager.set_location(Location(-33.8688, 151.2093))

    assert manager.snapshot.state == DeviceState.DISCONNECTED
    assert manager.snapshot.device is None
    assert manager.snapshot.location is None
    assert connection.close_calls == 1


@pytest.mark.asyncio
async def test_set_timeout_invalidates_uncertain_session(descriptor: DeviceDescriptor) -> None:
    connection = FakeConnection(descriptor, set_delay=0.05)
    manager = SessionManager(
        FakeAdapter(descriptor, connection=connection),
        timeouts=SessionTimeouts(set_location=0.01, disconnect=0.05),
    )

    await manager.connect(descriptor.identifier)

    with pytest.raises(GeoPortError) as raised:
        await manager.set_location(Location(-33.8688, 151.2093))

    assert raised.value.code == ErrorCode.OPERATION_TIMEOUT
    assert manager.snapshot.state == DeviceState.DISCONNECTED
    assert connection.close_calls == 1


@pytest.mark.asyncio
async def test_clear_is_idempotent_when_ready(descriptor: DeviceDescriptor) -> None:
    connection = FakeConnection(descriptor)
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))

    await manager.connect(descriptor.identifier)
    result = await manager.clear_location()

    assert result.state == DeviceState.READY
    assert connection.clear_calls == 0


@pytest.mark.asyncio
async def test_disconnect_clears_simulation_then_closes(descriptor: DeviceDescriptor) -> None:
    connection = FakeConnection(descriptor)
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))

    await manager.connect(descriptor.identifier)
    await manager.set_location(Location(-33.8688, 151.2093))
    result = await manager.disconnect()

    assert result.state == DeviceState.DISCONNECTED
    assert result.device is None
    assert result.location is None
    assert connection.clear_calls == 1
    assert connection.close_calls == 1


@pytest.mark.asyncio
async def test_mutating_operations_are_serialized(descriptor: DeviceDescriptor) -> None:
    set_started = asyncio.Event()
    set_release = asyncio.Event()
    connection = FakeConnection(
        descriptor,
        set_started=set_started,
        set_release=set_release,
    )
    manager = SessionManager(FakeAdapter(descriptor, connection=connection))

    await manager.connect(descriptor.identifier)

    set_task = asyncio.create_task(manager.set_location(Location(-33.8688, 151.2093)))
    await set_started.wait()
    clear_task = asyncio.create_task(manager.clear_location())
    await asyncio.sleep(0)

    assert manager.snapshot.state == DeviceState.SETTING_LOCATION
    assert not clear_task.done()

    set_release.set()
    await set_task
    clear_result = await clear_task

    assert clear_result.state == DeviceState.READY
    assert connection.clear_calls == 1


@pytest.mark.asyncio
async def test_set_while_disconnected_is_rejected_without_adapter_call(
    descriptor: DeviceDescriptor,
) -> None:
    adapter = FakeAdapter(descriptor)
    manager = SessionManager(adapter)

    with pytest.raises(InvalidStateError):
        await manager.set_location(Location(-33.8688, 151.2093))

    assert adapter.connect_calls == 0


@pytest.mark.asyncio
async def test_repeated_set_clear_does_not_create_extra_connections(
    descriptor: DeviceDescriptor,
) -> None:
    connection = FakeConnection(descriptor)
    adapter = FakeAdapter(descriptor, connection=connection)
    manager = SessionManager(adapter)

    await manager.connect(descriptor.identifier)
    for index in range(100):
        await manager.set_location(Location(-33.8688 + index / 100_000, 151.2093))
        await manager.clear_location()

    assert manager.snapshot.state == DeviceState.READY
    assert adapter.connect_calls == 1
    assert len(connection.set_calls) == 100
    assert connection.clear_calls == 100


def test_location_rejects_non_finite_and_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        Location(float("nan"), 151.0)
    with pytest.raises(ValueError):
        Location(-91.0, 151.0)
    with pytest.raises(ValueError):
        Location(-33.0, 181.0)

from fastapi.testclient import TestClient

from geoportlocal.app import create_app
from geoportlocal.domain.errors import ErrorCode, GeoPortError
from tests.fakes import FakeAdapter, FakeConnection, make_descriptor


def test_device_api_happy_path_tracks_authoritative_state() -> None:
    descriptor = make_descriptor()
    connection = FakeConnection(descriptor)
    adapter = FakeAdapter(descriptor, connection=connection)

    with TestClient(create_app(adapter)) as client:
        devices = client.get("/api/devices")
        assert devices.status_code == 200
        assert devices.json()["devices"][0]["identifier"] == descriptor.identifier

        connected = client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        assert connected.status_code == 200
        assert connected.json()["state"] == "ready"

        simulated = client.post(
            "/api/location",
            json={"latitude": -33.8688, "longitude": 151.2093},
        )
        assert simulated.status_code == 200
        assert simulated.json()["state"] == "simulating"

        status = client.get("/api/device/status")
        assert status.status_code == 200
        assert status.json()["state"] == "simulating"

        cleared = client.delete("/api/location")
        assert cleared.status_code == 200
        assert cleared.json()["state"] == "ready"

        disconnected = client.post("/api/device/disconnect")
        assert disconnected.status_code == 200
        assert disconnected.json()["state"] == "disconnected"


def test_failed_set_never_returns_success_or_simulating_state() -> None:
    descriptor = make_descriptor()
    connection = FakeConnection(
        descriptor,
        set_error=GeoPortError(ErrorCode.LOCATION_SET_FAILED, "Set failed.", retryable=True),
    )
    adapter = FakeAdapter(descriptor, connection=connection)

    with TestClient(create_app(adapter)) as client:
        client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        response = client.post(
            "/api/location",
            json={"latitude": -33.8688, "longitude": 151.2093},
        )

        assert response.status_code == 502
        assert response.json() == {
            "error": {
                "code": "LOCATION_SET_FAILED",
                "message": "Set failed.",
                "retryable": True,
            }
        }
        assert client.get("/api/device/status").json()["state"] == "ready"


def test_failed_connect_uses_stable_error_envelope() -> None:
    descriptor = make_descriptor()
    adapter = FakeAdapter(
        descriptor,
        connect_error=GeoPortError(
            ErrorCode.TUNNEL_UNAVAILABLE,
            "Tunnel unavailable.",
            retryable=True,
        ),
    )

    with TestClient(create_app(adapter)) as client:
        response = client.post("/api/device/connect", json={"identifier": descriptor.identifier})

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "TUNNEL_UNAVAILABLE"
        assert client.get("/api/device/status").json()["state"] == "disconnected"


def test_invalid_coordinates_are_rejected_before_device_call() -> None:
    descriptor = make_descriptor()
    connection = FakeConnection(descriptor)
    adapter = FakeAdapter(descriptor, connection=connection)

    with TestClient(create_app(adapter)) as client:
        client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        response = client.post(
            "/api/location",
            json={"latitude": -91, "longitude": 151.2093},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert connection.set_calls == []


def test_unknown_request_fields_are_rejected() -> None:
    descriptor = make_descriptor()
    adapter = FakeAdapter(descriptor)

    with TestClient(create_app(adapter)) as client:
        response = client.post(
            "/api/device/connect",
            json={"identifier": descriptor.identifier, "unexpected": "value"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert adapter.connect_calls == 0


def test_status_invalidates_idle_session_when_presence_probe_proves_absent() -> None:
    descriptor = make_descriptor()
    connection = FakeConnection(descriptor)

    async def absent(_: str) -> bool:
        return False

    app = create_app(
        FakeAdapter(descriptor, connection=connection),
        presence_probe=absent,
    )

    with TestClient(app) as client:
        connected = client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        assert connected.json()["state"] == "ready"

        status = client.get("/api/device/status")

    assert status.status_code == 200
    assert status.json()["state"] == "disconnected"
    assert status.json()["device"] is None
    assert connection.close_calls == 1


def test_status_preserves_session_when_presence_is_unknown() -> None:
    descriptor = make_descriptor()
    connection = FakeConnection(descriptor)

    async def unknown(_: str) -> None:
        return None

    app = create_app(
        FakeAdapter(descriptor, connection=connection),
        presence_probe=unknown,
    )

    with TestClient(app) as client:
        client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        status = client.get("/api/device/status")

    assert status.status_code == 200
    assert status.json()["state"] == "ready"
    assert connection.close_calls == 1  # lifespan shutdown only

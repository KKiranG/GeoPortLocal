import socket

import pytest
from fastapi.testclient import TestClient

from geoportlocal import __version__
from geoportlocal.__main__ import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    bind_listener,
    build_parser,
)
from geoportlocal.app import create_app
from tests.fakes import FakeAdapter, make_descriptor


def test_health_endpoint_is_local_app_health_only() -> None:
    with TestClient(create_app(FakeAdapter(make_descriptor()))) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "GeoPortLocal",
        "version": __version__,
    }


def test_launcher_defaults_to_loopback() -> None:
    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 54321
    assert build_parser().parse_args([]).port is None


def test_cli_accepts_explicit_local_port() -> None:
    args = build_parser().parse_args(["--port", "58424", "--no-browser"])

    assert args.port == 58424
    assert args.no_browser is True


def test_default_port_collision_falls_back_without_touching_owner() -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind((DEFAULT_HOST, 0))
    blocker.listen(1)
    occupied_port = int(blocker.getsockname()[1])

    listener = bind_listener(None, preferred_port=occupied_port)
    try:
        assert int(listener.getsockname()[1]) != occupied_port
        assert listener.getsockname()[0] == DEFAULT_HOST
    finally:
        listener.close()
        blocker.close()


def test_explicit_busy_port_fails_instead_of_killing_process() -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind((DEFAULT_HOST, 0))
    blocker.listen(1)
    occupied_port = int(blocker.getsockname()[1])

    try:
        with pytest.raises(SystemExit, match="unavailable"):
            bind_listener(occupied_port)
    finally:
        blocker.close()


def test_browser_ui_and_local_static_assets_are_served_with_security_headers() -> None:
    with TestClient(create_app(FakeAdapter(make_descriptor()))) as client:
        page = client.get("/")
        javascript = client.get("/static/app.js")
        stylesheet = client.get("/static/app.css")

    assert page.status_code == 200
    assert "GeoPortLocal" in page.text
    assert "Device truth only" in page.text
    assert javascript.status_code == 200
    assert stylesheet.status_code == 200

    policy = page.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "connect-src 'self'" in policy
    assert "img-src 'self' https://tile.openstreetmap.org" in policy
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["x-frame-options"] == "DENY"
    assert page.headers["referrer-policy"] == "no-referrer"


def test_non_loopback_host_header_is_rejected() -> None:
    with TestClient(create_app(FakeAdapter(make_descriptor()))) as client:
        response = client.get("/api/health", headers={"host": "attacker.example"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_cross_site_browser_mutation_is_rejected_without_state_change() -> None:
    descriptor = make_descriptor()
    app = create_app(FakeAdapter(descriptor))

    with TestClient(app) as client:
        connected = client.post("/api/device/connect", json={"identifier": descriptor.identifier})
        assert connected.json()["state"] == "ready"

        rejected = client.post(
            "/api/device/disconnect",
            headers={
                "origin": "https://attacker.example",
                "sec-fetch-site": "cross-site",
            },
        )
        status = client.get("/api/device/status")

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "INVALID_REQUEST"
    assert status.json()["state"] == "ready"

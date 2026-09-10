from fastapi.testclient import TestClient

from geoportlocal import __version__
from geoportlocal.__main__ import DEFAULT_HOST, DEFAULT_PORT, build_parser
from geoportlocal.app import create_app


def test_health_endpoint_is_local_app_health_only() -> None:
    client = TestClient(create_app())

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


def test_cli_accepts_explicit_local_port() -> None:
    args = build_parser().parse_args(["--port", "58424"])

    assert args.port == 58424

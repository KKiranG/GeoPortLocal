"""GeoPortLocal ASGI application bootstrap."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from geoportlocal import __version__
from geoportlocal.api.errors import install_error_handlers
from geoportlocal.api.routes_device import router as device_router
from geoportlocal.api.routes_fuel import router as fuel_router
from geoportlocal.device.adapter import DeviceAdapter
from geoportlocal.device.presence import PresenceProbe
from geoportlocal.device.session import SessionManager
from geoportlocal.fuel.provider import FuelProvider
from geoportlocal.fuel.service import FuelService
from geoportlocal.web.routes import WEB_ROOT, router as web_router


def create_app(
    adapter: DeviceAdapter | None = None,
    fuel_provider: FuelProvider | None = None,
    presence_probe: PresenceProbe | None = None,
) -> FastAPI:
    """Create the local GeoPortLocal application and own its runtime resources."""
    using_default_adapter = adapter is None
    if adapter is None:
        from geoportlocal.device.pymobiledevice import PymobileDeviceAdapter

        adapter = PymobileDeviceAdapter()

    if using_default_adapter and presence_probe is None:
        from geoportlocal.device.presence import probe_device_presence

        presence_probe = probe_device_presence

    if fuel_provider is None:
        from geoportlocal.fuel.project_zero_three import ProjectZeroThreeProvider

        fuel_provider = ProjectZeroThreeProvider()

    session_manager = SessionManager(adapter)
    fuel_service = FuelService(fuel_provider)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await session_manager.shutdown()
            await fuel_service.close()

    app = FastAPI(
        title="GeoPortLocal",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.session_manager = session_manager
    app.state.fuel_service = fuel_service
    app.state.presence_probe = presence_probe

    install_error_handlers(app)
    app.include_router(device_router)
    app.include_router(fuel_router)
    app.mount("/static", StaticFiles(directory=str(WEB_ROOT / "static")), name="static")
    app.include_router(web_router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        # Deliberately does not contact a phone, fuel provider, map provider or Internet service.
        return {
            "status": "ok",
            "app": "GeoPortLocal",
            "version": __version__,
        }

    return app

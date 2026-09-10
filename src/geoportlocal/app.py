"""GeoPortLocal ASGI application bootstrap."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from geoportlocal import __version__
from geoportlocal.api.errors import install_error_handlers
from geoportlocal.api.routes_device import router as device_router
from geoportlocal.device.adapter import DeviceAdapter
from geoportlocal.device.session import SessionManager


def create_app(adapter: DeviceAdapter | None = None) -> FastAPI:
    """Create the local GeoPortLocal application with an owned device session."""
    if adapter is None:
        from geoportlocal.device.pymobiledevice import PymobileDeviceAdapter

        adapter = PymobileDeviceAdapter()

    session_manager = SessionManager(adapter)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await session_manager.shutdown()

    app = FastAPI(
        title="GeoPortLocal",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.session_manager = session_manager
    install_error_handlers(app)
    app.include_router(device_router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": "GeoPortLocal",
            "version": __version__,
        }

    return app

"""GeoPortLocal ASGI application bootstrap."""

from fastapi import FastAPI

from geoportlocal import __version__


def create_app() -> FastAPI:
    """Create the local GeoPortLocal application."""
    app = FastAPI(
        title="GeoPortLocal",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": "GeoPortLocal",
            "version": __version__,
        }

    return app


app = create_app()

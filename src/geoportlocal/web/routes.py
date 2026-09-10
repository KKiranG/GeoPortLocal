"""Routes for the local GeoPortLocal browser UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from geoportlocal import __version__

WEB_ROOT = Path(__file__).resolve().parent
_templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "GeoPortLocal", "version": __version__},
    )

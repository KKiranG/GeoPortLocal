"""Request models for the GeoPortLocal local API."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: Annotated[str, Field(min_length=1)]


class LocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]

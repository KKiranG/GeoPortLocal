# GeoPortLocal target architecture

Date: 2026-09-10

## 1. Architectural decision

GeoPortLocal will keep a browser-based local UI and replace the legacy all-in-one Flask/thread/tunnel runtime with a small asynchronous application core.

The preferred backend is **FastAPI + uvicorn**, not because a new web framework is itself valuable, but because the current `pymobiledevice3` Python API is asyncio-native and a persistent device session must live on one coherent event loop. Retaining synchronous Flask would require a dedicated event-loop thread or repeated loop creation across requests, reproducing the lifecycle complexity being removed.

The UI remains plain HTML/CSS/JavaScript + Leaflet. Do not add React/Vue/Svelte.

## 2. Module layout

Target layout:

```text
src/
  geoportlocal/
    __init__.py
    __main__.py
    app.py
    config.py
    logging.py

    domain/
      device.py
      errors.py
      fuel.py

    device/
      adapter.py
      pymobiledevice.py
      session.py

    fuel/
      provider.py
      project_zero_three.py
      cache.py

    api/
      models.py
      routes_device.py
      routes_fuel.py
      routes_health.py

    web/
      templates/
        index.html
      static/
        app.js
        app.css

tests/
  unit/
  api/
  integration/
```

Do not copy `src/main.py` into the new package and split it mechanically. New modules are written around explicit contracts; only proven useful parsing/UI logic is migrated.

## 3. Domain model

### DeviceDescriptor

```python
@dataclass(frozen=True, slots=True)
class DeviceDescriptor:
    identifier: str
    name: str | None
    product_type: str | None
    ios_version: str | None
    connection: Literal["usb", "network", "unknown"]
```

The raw UDID is required internally for device selection but is redacted in logs. Do not expose pair records or RSD internals through this model.

### DeviceState

```python
class DeviceState(StrEnum):
    DISCONNECTED = "disconnected"
    DISCOVERING = "discovering"
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    READY = "ready"
    SIMULATING = "simulating"
    CLEARING = "clearing"
    DISCONNECTING = "disconnecting"
    ERROR = "error"
```

State is authoritative server-side. JavaScript never invents a state transition merely because a button was clicked.

### Location

```python
@dataclass(frozen=True, slots=True)
class Location:
    latitude: float
    longitude: float
```

Validation:

- latitude: `-90 <= value <= 90`
- longitude: `-180 <= value <= 180`
- finite numbers only; reject NaN and infinity.

### FuelQuote

Normalized provider output:

```python
@dataclass(frozen=True, slots=True)
class FuelQuote:
    region: str
    fuel_type: str
    price_cents_per_litre: float
    latitude: float
    longitude: float
    station_name: str | None
    source_updated_at: datetime | None
    fetched_at: datetime
    stale: bool
```

If the upstream provider lacks one optional field, keep it `None`; do not fabricate station names or timestamps.

## 4. Device adapter contract

Application code depends on a project-owned interface rather than `pymobiledevice3` directly.

```python
class DeviceAdapter(Protocol):
    async def discover(self) -> list[DeviceDescriptor]: ...
    async def connect(self, identifier: str) -> "DeviceConnection": ...

class DeviceConnection(Protocol):
    @property
    def descriptor(self) -> DeviceDescriptor: ...

    async def set_location(self, location: Location) -> None: ...
    async def clear_location(self) -> None: ...
    async def close(self) -> None: ...
```

Tests use `FakeDeviceAdapter` and `FakeDeviceConnection`. HTTP code does not mock `pymobiledevice3` internals.

## 5. `pymobiledevice3` adapter

### Discovery

Use the smallest current public mechanism that reliably provides connected-device identifiers and metadata. Discovery and metadata loading are separate error boundaries:

1. enumerate physical/logical devices;
2. for each device, attempt metadata enrichment;
3. if metadata enrichment fails, return the discovered device with nullable metadata plus a diagnostic rather than silently dropping the entire list;
4. never mutate the device's Wi-Fi connection setting merely because the list endpoint was called.

### Modern iOS connection

For iOS 17.4+ developer services:

```python
from pymobiledevice3.remote.rsd_tunnel import PreferredRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
```

The connection object owns the context-manager stack:

```text
PreferredRsdTunnel(identifier)
    -> RemoteServiceDiscoveryService
        -> DvtProvider
            -> LocationSimulation
```

Conceptual lifecycle:

```python
self._rsd_tunnel = PreferredRsdTunnel(serial=identifier)
rsd = await self._rsd_tunnel.__aenter__()

self._dvt = DvtProvider(rsd)
dvt = await self._dvt.__aenter__()

self._location = LocationSimulation(dvt)
await self._location.__aenter__()
```

Closing unwinds in reverse order and is protected so partial construction also cleans up.

Do not expose `rsd_host` or `rsd_port` outside the adapter. GeoPortLocal should never need to cache them for normal modern operation.

### Set

```python
await self._location.set(latitude, longitude)
```

The method returns only after the call completes. Any exception is translated to a GeoPortLocal domain error and invalidates the session when the exception indicates transport loss.

### Clear

```python
await self._location.clear()
```

`clear_location()` must be safe to call when the session believes it is already clear. If upstream requires an active channel and that channel is gone, SessionManager reports the transport failure truthfully and completes local cleanup.

### iOS compatibility

The adapter must inspect the actual device version, not trust an arbitrary version string posted by the browser.

Initial rules:

- iOS >=17.4: normal modern adapter.
- iOS 17.0-17.3.1: return a specific compatibility error until the privileged compatibility adapter is deliberately implemented.
- iOS <17: do not silently route through fake RSD tuple state. Either implement a tested legacy lockdown adapter or report unsupported in the first milestone.

## 6. SessionManager

`SessionManager` is the single authority for mutating device lifecycle.

State fields:

```text
_state
_selected_device
_connection
_last_error
_operation_lock
```

No Flask/FastAPI route may hold its own device globals.

### Serialization

Every mutating operation acquires one `asyncio.Lock`:

- connect
- set location
- clear location
- disconnect
- shutdown cleanup

This prevents overlapping set/clear/connect calls and removes the need for ad-hoc global terminate flags.

### Timeouts

Initial defaults:

```text
discovery:     5 s
connect:      20 s
set location: 10 s
clear:        10 s
disconnect:    5 s
```

Implement with `asyncio.timeout()` / `asyncio.wait_for()` at the application boundary. A timeout is an operation failure, not success-with-warning.

These values are configuration constants and may be adjusted only after hardware evidence is recorded.

### Connect algorithm

```text
require state in {DISCONNECTED, DISCOVERED, ERROR}
state = CONNECTING
close any stale owned connection defensively
connection = await adapter.connect(id) with timeout
if success:
    store connection
    state = READY
else:
    clear connection
    state = ERROR
    cleanup
    state = DISCONNECTED (while preserving last_error)
    raise domain error
```

A partially created object is never stored as a reusable connection.

### Set algorithm

```text
require READY or SIMULATING
state = SIMULATING_PENDING internally if needed; public state remains operation-specific
await connection.set_location(location) with timeout
on success: state = SIMULATING
on failure:
    if transport invalid -> destroy session -> DISCONNECTED
    otherwise -> READY with last_error
    raise
```

Do not return HTTP 200 before the awaited call completes.

### Clear algorithm

```text
if READY: return success (already clear)
require SIMULATING
state = CLEARING
await connection.clear_location() with timeout
on success: state = READY
on transport failure: destroy session -> DISCONNECTED
```

### Disconnect algorithm

```text
if already DISCONNECTED: success
state = DISCONNECTING
try clear if known SIMULATING and service is alive
close connection
clear local references
state = DISCONNECTED
```

Cleanup must continue even if clear fails.

## 7. Error taxonomy

Create project exceptions with stable codes:

```text
DEVICE_NOT_FOUND
DEVICE_METADATA_FAILED
DEVICE_NOT_TRUSTED
DEVELOPER_MODE_REQUIRED
IOS_VERSION_UNSUPPORTED
TUNNEL_UNAVAILABLE
DEVICE_DISCONNECTED
LOCATION_SET_FAILED
LOCATION_CLEAR_FAILED
OPERATION_TIMEOUT
FUEL_PROVIDER_UNAVAILABLE
FUEL_PROVIDER_INVALID_RESPONSE
INVALID_REQUEST
INTERNAL_ERROR
```

Each error has:

- code;
- user-safe message;
- optional debug cause kept server-side;
- retryable boolean where meaningful.

The UI renders code + user-safe message. It does not display arbitrary Python exception strings by default.

## 8. HTTP API contract

### `GET /api/health`

No Internet or phone operation.

Response:

```json
{
  "status": "ok",
  "app": "GeoPortLocal",
  "version": "..."
}
```

### `GET /api/devices`

Performs discovery with a bounded timeout.

Response:

```json
{
  "devices": [
    {
      "identifier": "...",
      "name": "iPhone",
      "product_type": "iPhone...",
      "ios_version": "26.5",
      "connection": "usb"
    }
  ]
}
```

### `POST /api/device/connect`

Request:

```json
{"identifier": "..."}
```

Response after completed connect:

```json
{"state": "ready", "device": {...}}
```

### `GET /api/device/status`

Returns authoritative state and last safe error.

### `POST /api/location`

Request:

```json
{"latitude": -33.8688, "longitude": 151.2093}
```

Success means the underlying simulation call completed:

```json
{"state": "simulating", "location": {...}}
```

### `DELETE /api/location`

Success:

```json
{"state": "ready"}
```

### `POST /api/device/disconnect`

Success:

```json
{"state": "disconnected"}
```

### Error envelope

```json
{
  "error": {
    "code": "TUNNEL_UNAVAILABLE",
    "message": "Could not establish a developer-service connection to the selected device.",
    "retryable": true
  }
}
```

Use appropriate HTTP status codes; do not encode every failure as HTTP 200.

## 9. Local server and port ownership

Bind only to `127.0.0.1` by default.

Do not perform the legacy sequence “check port, then later bind,” because another process can race between those operations. Let the server bind a requested port directly; on address-in-use, select a free loopback port through an OS-assigned socket or use port `0` during launcher setup, then pass the bound port to the browser launcher.

Never kill processes merely because their executable name contains `GeoPort`.

The old GeoPort application and GeoPortLocal must be able to run independently. GeoPortLocal must not terminate old GeoPort and vice versa.

## 10. Fuel service

`FuelService` owns provider access and caching.

Initial network policy:

```text
connect timeout: 3 s
read timeout:    5 s
retries:         1 retry for transport/5xx only
retry delay:     0.5 s
```

No retry for schema/validation failures.

A valid last-good response can be cached for UI resilience. Cache state must expose `stale=true` when serving data older than the provider's latest successful fetch.

Do not call the fuel provider during application startup. Fetch only when fuel UI requests it or through an explicit background refresh after the local server is already healthy.

The device API must remain fully functional with DNS disabled.

## 11. Frontend state model

Frontend buttons are pure projections of server state.

Example:

```text
disconnected -> Connect enabled; Simulate/Clear disabled
ready        -> Simulate enabled; Clear disabled
simulating   -> Simulate optional/update; Clear enabled
clearing     -> mutating buttons disabled
connecting   -> mutating buttons disabled
error        -> show exact local error; reconnect path available
```

The browser polls `/api/device/status` only if required. Prefer returning state from every mutation and updating from those responses.

## 12. Migration mapping from legacy source

Legacy concept -> modern home:

```text
list_devices / py_list_devices  -> device/pymobiledevice.py::discover
connect_device/connect_usb      -> device/session.py + adapter.connect
rsd_data_map                    -> removed
start_*_tunnel_thread           -> removed from app; PreferredRsdTunnel owns transport
set_location_thread             -> DeviceConnection.set_location
start_set_location_thread       -> removed
terminate_location_thread       -> removed
stop_location                   -> SessionManager.clear_location
clear_geoport                   -> removed
terminate_threads               -> removed
fetch_api_data                  -> fuel/project_zero_three.py
/api/data/<fuel_type>           -> api/routes_fuel.py
/update_location global         -> removed; coordinate is supplied to POST /api/location
get_country_from_ip             -> removed
GitHub broadcast/version call   -> removed from startup
```

## 13. Logging

Default INFO log examples:

```text
app_started version=...
device_discovered device=***401C connection=usb ios=26.4.2
connect_started device=***401C
connect_succeeded device=***401C duration_ms=...
location_set_succeeded device=***401C duration_ms=...
device_disconnected device=***401C reason=physical_disconnect
fuel_fetch_failed provider=project_zero_three error=timeout
```

Rules:

- redact identifiers to last 4 characters;
- no pair-record contents;
- no auth data;
- no blanket dependency DEBUG logging in normal use;
- include stack traces in explicit debug mode only.

## 14. Shutdown

FastAPI lifespan owns application resources.

On shutdown:

1. acquire SessionManager mutation lock;
2. attempt clear if simulation is active and the service is live;
3. close the device connection/context stack;
4. close HTTP client for fuel provider;
5. exit.

There is no `os._exit()`, process-name scanning, synthetic thread termination or SIGINT sent to self.

## 15. Architectural acceptance criteria

The architecture is considered implemented when:

- application routes import no `pymobiledevice3` modules;
- only `device/pymobiledevice.py` knows `pymobiledevice3` specifics;
- no RSD host/port appears in application/domain/API state;
- no device lifecycle depends on module-level mutable globals;
- there is no per-click thread creation;
- all device mutations are awaited;
- all state transitions have unit coverage;
- device runtime works without Internet access;
- fuel runtime works without a connected device;
- local server binds loopback only;
- old GeoPort can coexist with GeoPortLocal.
# GeoPortLocal architecture

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Status: hardware-independent architecture implemented; target Mac/iPhone qualification pending

## 1. Decision

GeoPortLocal keeps the useful browser workflow from GeoPort but replaces the legacy Flask/global/thread/manual-tunnel runtime with one asyncio-native application core.

Backend: **FastAPI + uvicorn**. The reason is lifecycle coherence: the current `pymobiledevice3` API used by the modern device path is asynchronous, and one persistent device connection should live on one event loop rather than behind per-request loop/thread bridges.

Frontend: **local plain HTML/CSS/JavaScript**. No React/Vue/Svelte, Bootstrap or jQuery. No remote JavaScript is loaded into the localhost control origin. The map picker is implemented locally; OpenStreetMap is used only for image tiles and may fail without affecting device control.

## 2. Implemented module layout

```text
src/geoportlocal/
  __init__.py
  __main__.py              launcher, loopback listener and browser start
  app.py                   FastAPI composition/lifespan

  domain/
    device.py              immutable device/location/session models
    errors.py              stable project error codes
    fuel.py                normalized fuel snapshot models

  device/
    adapter.py             project-owned protocols
    pymobiledevice.py      only normal device-integration module that knows pymobiledevice3
    presence.py            cheap usbmux presence probe for idle disconnects
    session.py             single lifecycle/state authority

  fuel/
    provider.py            provider protocol
    project_zero_three.py  external PZT adapter/validation
    service.py             fresh + last-good cache semantics

  api/
    models.py              strict request validation
    errors.py              error-to-HTTP mapping
    serialization.py       canonical response payloads
    routes_device.py
    routes_fuel.py

  runtime/
    logging.py             redacting formatter and short device identifiers

  web/
    routes.py
    templates/index.html
    static/app.css
    static/app.js

tests/
  fakes.py
  test_session.py
  test_api.py
  test_fuel.py
  test_fuel_api.py
  test_bootstrap.py
  test_logging.py
  test_pymobiledevice_adapter.py
```

Legacy `src/main.py` and `src/templates/map*.html` remain untouched on this branch as reference/fallback material. They are not imported by the new runtime.

## 3. Device domain and state machine

`DeviceDescriptor` contains only the application fields needed to identify and display a device: identifier, optional name/product type/iOS version and connection kind. The full identifier is needed internally for device selection but routine logs use a short suffix and the process-wide formatter redacts common full UDID forms if they enter a message or traceback.

`Location` requires finite numbers with:

```text
-90 <= latitude  <= 90
-180 <= longitude <= 180
```

The public device states implemented in `domain/device.py` are:

```text
DISCONNECTED
DISCOVERING
DISCOVERED
CONNECTING
READY
SETTING_LOCATION
SIMULATING
CLEARING
DISCONNECTING
ERROR
```

The state is authoritative on the server. Browser buttons are projections of returned state; JavaScript does not turn a click into assumed success.

Normal successful path:

```text
DISCONNECTED
  -> DISCOVERING
  -> DISCOVERED
  -> CONNECTING
  -> READY
  -> SETTING_LOCATION
  -> SIMULATING
  -> CLEARING
  -> READY
  -> DISCONNECTING
  -> DISCONNECTED
```

`ERROR` is an internal transition used while invalidating a broken connection; an unusable transport is not retained as a reusable session.

## 4. Project-owned device boundary

Application/API code depends on two protocols:

```python
class DeviceAdapter(Protocol):
    async def discover(self) -> list[DeviceDescriptor]: ...
    async def connect(self, identifier: str) -> DeviceConnection: ...

class DeviceConnection(Protocol):
    @property
    def descriptor(self) -> DeviceDescriptor: ...
    async def set_location(self, location: Location) -> None: ...
    async def clear_location(self) -> None: ...
    async def close(self) -> None: ...
```

This isolates dependency churn. Tests use fake adapters/connections; API tests do not mock internal `pymobiledevice3` objects.

## 5. Current pymobiledevice3 adapter

The branch pins `pymobiledevice3==11.12.1`, current at the research cutoff of 2026-09-10. Application code does not import `pymobiledevice3.cli.*` internals.

### Discovery

`PymobileDeviceAdapter.discover()`:

1. awaits `pymobiledevice3.usbmux.list_devices()`;
2. deduplicates USB/network representations by identifier and prefers USB for the desktop workflow;
3. attempts metadata enrichment using `create_using_usbmux(..., autopair=False)`;
4. if metadata enrichment fails, keeps the physical device row with nullable metadata instead of silently hiding it.

Discovery never enables Wi-Fi connections or changes device configuration.

### Connect preflight

For the selected identifier, the adapter:

1. re-enumerates to avoid connecting to a stale browser row;
2. opens lockdown with `autopair=True` and bounded pair timeout;
3. reads authoritative device metadata from the phone;
4. requires iOS 17.4 or newer in the first modern milestone;
5. checks Developer Mode and returns `DEVELOPER_MODE_REQUIRED` if disabled;
6. closes the lockdown preflight context;
7. creates the actual developer-service stack.

GeoPortLocal does not remove a passcode or force-enable Developer Mode.

### Developer-service stack

The real `PymobileDeviceConnection` owns one `AsyncExitStack`:

```text
PreferredRsdTunnel(serial=identifier)
  -> RemoteServiceDiscoveryService
    -> DvtProvider
      -> LocationSimulation
```

Opening any inner layer unsuccessfully causes the already-entered layers to unwind before an error is returned. The connection is stored by `SessionManager` only after this complete stack has opened successfully.

No RSD address or port escapes into application/domain/API state.

### Set and clear

Current dependency calls are awaited directly:

```python
await location_service.set(latitude, longitude)
await location_service.clear()
```

HTTP success therefore means the dependency call completed, not that a detached worker thread was started.

## 6. iOS compatibility policy

Initial qualification target:

```text
iOS >= 17.4  -> modern adapter
17.0-17.3.1  -> explicit unsupported result in this milestone
< 17          -> explicit unsupported result until a separate tested adapter is justified
```

Do not reintroduce the legacy hand-maintained `rsd_host`/`rsd_port` tuple cache to broaden old-version support.

## 7. SessionManager invariants

`SessionManager` is the single authority for mutable device lifecycle. It owns:

```text
adapter
one asyncio mutation lock
current state
device descriptor
one DeviceConnection or None
current simulated Location or None
last safe GeoPortError or None
```

All discovery/connect/set/clear/disconnect operations are serialized with the same lock. There is no per-click thread creation and no global terminate flags.

Timeout defaults:

```text
discovery      5 s
connect       20 s
set location  10 s
clear         10 s
disconnect     5 s
```

Timeout at the application boundary is failure, never success-with-warning.

### Failed connect

A failed connect leaves no connection object cached. If an adapter somehow returns a connection for a different identifier, that connection is closed and treated as an internal failure.

### Set failure

Before the call, state becomes `SETTING_LOCATION`.

On success:

```text
location stored -> SIMULATING
```

On non-transport failure:

```text
restore previous READY/SIMULATING state and previous location -> retain last_error -> raise
```

On `DEVICE_DISCONNECTED`, `TUNNEL_UNAVAILABLE` or `OPERATION_TIMEOUT`:

```text
remove connection/device/location -> best-effort close old connection -> DISCONNECTED -> raise
```

A set timeout is deliberately conservative. It can be ambiguous whether the device received the command immediately before communication was lost, so GeoPortLocal discards the uncertain session rather than reusing it.

### Clear

Clear is idempotent when state is already `READY`. From `SIMULATING`, state becomes `CLEARING`; success returns to `READY`. Transport failure invalidates the session.

### Disconnect/shutdown

If simulation is known active, disconnect first attempts clear. It then closes the owned connection even if clear failed, removes all local references and ends `DISCONNECTED`. FastAPI lifespan calls this same cleanup during graceful server shutdown.

## 8. Idle physical-disconnect detection

A session can otherwise remain visually `READY` if a cable is removed while no operation is running. GeoPortLocal solves this without restoring a background watcher thread.

The browser polls `/api/device/status` approximately every 2.5 seconds **only while a session exists**. The status route invokes a cheap `usbmux.list_devices()` presence probe:

```text
identifier present -> preserve session
successful enumeration + identifier absent -> disconnect/invalidate session
probe itself failed -> presence unknown; do not destroy a potentially healthy session
```

Only positive evidence of absence invalidates idle state.

## 9. Error taxonomy

Stable project codes include:

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
INVALID_STATE
INVALID_REQUEST
INTERNAL_ERROR
```

A `GeoPortError` carries code, user-safe message, retryability and an optional internal cause. API responses do not return arbitrary dependency exception strings.

## 10. HTTP API

Implemented routes:

```text
GET    /api/health
GET    /api/devices
POST   /api/device/connect
GET    /api/device/status
POST   /api/location
DELETE /api/location
POST   /api/device/disconnect
GET    /api/fuel/regions
GET    /api/fuel/types?region=...
GET    /api/fuel/quote?region=...&type=...
GET    /
GET    /static/*
```

`/api/health` deliberately performs no phone, fuel-provider, map or Internet operation.

Location mutation input is strict JSON containing only finite latitude/longitude values. Unknown fields are rejected.

Error envelope:

```json
{
  "error": {
    "code": "TUNNEL_UNAVAILABLE",
    "message": "Could not establish the iOS developer-service connection.",
    "retryable": true
  }
}
```

Failures use non-2xx status codes; they are not encoded as successful HTTP 200 responses.

## 11. Local listener and coexistence

The launcher binds only to `127.0.0.1`.

When no `--port` is supplied:

1. atomically attempt to bind/listen on 54321;
2. if it is occupied, close that failed socket and bind port 0 on loopback;
3. pass the already-bound listener to uvicorn;
4. print/open the actual chosen URL.

This removes both the old kill-by-process-name behavior and the check-then-bind race. An explicitly requested busy `--port` fails clearly rather than choosing a different port behind the user's back.

The old GeoPort application may remain installed or even own 54321; GeoPortLocal does not terminate it.

## 12. Fuel boundary

`ProjectZeroThreeProvider` is isolated because GeoPortLocal does not own its schema or availability.

Network policy implemented:

```text
HTTPS with normal certificate verification
connect timeout  3 s
read timeout     5 s
maximum attempts 2
retry delay      0.5 s
retry only transport/5xx
no retry for 4xx or schema failures
```

The provider validates/normalizes upstream objects into:

```text
region
fuel_type
price_cents_per_litre
suburb | None
state | None
latitude
longitude
fetched_at
stale
```

`FuelService` serializes refreshes, reuses a successful snapshot for 60 seconds and may return the last successful snapshot as explicitly stale if a later provider fetch fails.

A fuel outage cannot make `/api/health` or device operations fail.

## 13. Browser UI trust model

All executable HTML/CSS/JavaScript is served from the GeoPortLocal package itself. The page does not load a CDN JavaScript framework/library.

The map renderer performs local Web-Mercator coordinate conversion and requests only OpenStreetMap image tiles. If image tiles fail, the direct coordinate fields, fuel coordinates and every device operation remain usable.

Browser behavior:

```text
refresh -> discover devices
connect -> wait for server READY
set -> wait for server SIMULATING
clear -> wait for server READY
disconnect -> wait for server DISCONNECTED
```

Selecting a fuel quote updates the coordinate picker and map center only. It does **not** automatically call the device location endpoint.

The UI explicitly states that GeoPortLocal proves only its own simulation-operation boundary. A third-party application's acceptance/rejection is not used as device-health evidence.

## 14. Logging and privacy

Normal runtime logging is INFO-level with a process-wide `RedactingFormatter`.

Routine session messages log a shortened device suffix such as `***401C`, never coordinates. The formatter also redacts common modern/legacy UDID forms and labelled `udid`/`serial` values if a dependency puts them into a message or traceback.

Examples:

```text
device_discovery_succeeded count=1 duration_ms=...
connect_started device=***401C
connect_succeeded device=***401C duration_ms=...
location_set_succeeded device=***401C duration_ms=...
location_clear_failed device=***401C code=... duration_ms=...
disconnect_completed device=***401C cleanup_code=none duration_ms=...
```

No pair-record contents, authentication material or exact location coordinates belong in normal logs.

## 15. Packaging

Development metadata targets Python 3.14 and a generated `uv.lock` is the first local reproducibility artifact.

The first macOS qualification package is deliberately a PyInstaller **onedir** app bundle:

```text
GeoPortLocal.app
bundle id: io.github.kkirang.geoportlocal
```

The spec includes the local web data and uses PyInstaller's `collect_all("pymobiledevice3")` for the first reliability build because the dependency has dynamic/runtime-loaded pieces. Bundle-size pruning is deferred until a packaged hardware path is proven.

The build must remain side-by-side with the existing GeoPort app.

## 16. Migration mapping

```text
legacy list_devices/py_list_devices    -> PymobileDeviceAdapter.discover
legacy connect_device/connect_usb      -> SessionManager + adapter.connect
legacy rsd_data_map                    -> removed
legacy manual tunnel threads           -> PreferredRsdTunnel-owned transport
legacy set_location_thread             -> awaited DeviceConnection.set_location
legacy terminate_location_thread       -> removed
legacy stop_location                   -> SessionManager.clear_location
legacy terminate_threads/process kill  -> removed
legacy fetch_api_data                  -> ProjectZeroThreeProvider/FuelService
legacy /api/data/<fuel_type>           -> /api/fuel/*
legacy update_location global          -> explicit POST /api/location payload
legacy IP-country lookup               -> removed
legacy GitHub broadcast/update startup -> removed
legacy CDN JS framework stack          -> local browser code
```

## 17. Architectural acceptance gate

Hardware-independent architecture is complete when the locked local test gate confirms that:

- API/application routes do not know RSD host/port details;
- `pymobiledevice3` integration remains behind the device module boundary;
- no device lifecycle uses module-level mutable global connection state;
- no per-click/location/tunnel thread exists;
- device mutations are awaited and serialized;
- failed/timeout sessions cannot be reused;
- idle physical absence can invalidate a session without a watcher thread;
- device runtime does not depend on Internet/fuel/map services;
- fuel runtime does not depend on an iPhone;
- the HTTP listener is loopback-only and does not kill a conflicting process;
- local executable web assets contain no remote JavaScript dependency;
- normal logs redact device identifiers;
- the old GeoPort application can coexist with GeoPortLocal.

Actual readiness for daily use additionally requires the observed hardware/package gates in `docs/LOCAL_BOOTSTRAP.md` and `docs/TEST_MATRIX.md`. Repository inspection alone cannot satisfy those rows.

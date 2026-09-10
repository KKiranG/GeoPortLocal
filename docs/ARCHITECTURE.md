# GeoPortLocal architecture

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Status: hardware-independent implementation complete; target Mac/iPhone qualification pending

## 1. Decision

GeoPortLocal keeps the useful browser workflow from GeoPort but replaces the legacy Flask/global/thread/manual-tunnel runtime with one asyncio-native application core.

Backend: **FastAPI + uvicorn**. The current `pymobiledevice3` path is asynchronous, so one persistent device connection lives on one event loop rather than behind per-request loop/thread bridges.

Frontend: **local plain HTML/CSS/JavaScript**. No React/Vue/Svelte, Bootstrap, jQuery or remote executable JavaScript. The project-owned map picker performs Web-Mercator conversion locally; OpenStreetMap is used only for image tiles and may fail without affecting device control.

## 2. Implemented module layout

```text
src/geoportlocal/
  __init__.py
  __main__.py              loopback listener, uvicorn launch, browser start
  app.py                   FastAPI composition, security middleware, lifespan

  domain/
    device.py              immutable device/location/session models
    errors.py              stable project error codes
    fuel.py                normalized fuel snapshot models

  device/
    adapter.py             project-owned protocols
    pymobiledevice.py      pymobiledevice3 boundary
    presence.py            cheap usbmux presence probe
    session.py             single lifecycle/state authority

  fuel/
    provider.py            provider protocol
    project_zero_three.py  external provider adapter/validation
    service.py             fresh + last-good cache semantics

  api/
    models.py              strict request validation
    errors.py              expected + unexpected HTTP error sanitization
    serialization.py       canonical response payloads
    routes_device.py
    routes_fuel.py

  runtime/
    logging.py             redacted stream + bounded persistent log
    security.py            Host/origin/CSP/browser security boundary

  web/
    routes.py
    templates/index.html
    static/app.css
    static/app.js
```

Legacy `src/main.py` and `src/templates/map*.html` remain untouched and are not imported by the modern runtime.

## 3. Device state and truth model

`Location` accepts finite values only:

```text
-90 <= latitude <= 90
-180 <= longitude <= 180
```

Authoritative server states are:

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

Normal successful set/clear flow:

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

`READY` means GeoPortLocal owns a live device session and this process does not currently record a simulated coordinate. It does **not** prove that a previous crashed/terminated process left no simulation on the phone. Consequently an explicit Clear from READY is a real recovery operation and calls the device service; it is not optimized away as a no-op.

Browser controls are projections of returned server state. A button click is never treated as proof of success.

## 4. Project-owned device boundary

Application/API code depends on protocols rather than `pymobiledevice3` directly:

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

Only the device integration module knows `pymobiledevice3` internals. HTTP tests use fake adapters rather than mocking dependency internals.

## 5. Current pymobiledevice3 path

The branch pins `pymobiledevice3==11.12.1` at the 2026-09-10 research cutoff.

Discovery:

1. `await usbmux.list_devices()`;
2. deduplicate USB/network representations and prefer USB;
3. attempt metadata enrichment with `create_using_usbmux(..., autopair=False)`;
4. if metadata lookup fails, retain the physically discovered device with nullable metadata rather than hiding it.

Connection preflight:

1. re-enumerate selected identifier;
2. open lockdown with `autopair=True` and bounded pair timeout;
3. use authoritative device metadata;
4. require iOS 17.4+ for the first modern milestone;
5. require Developer Mode;
6. close lockdown preflight;
7. open the developer-service stack.

Owned developer-service stack:

```text
PreferredRsdTunnel(serial=identifier)
-> DvtProvider
-> LocationSimulation
```

The exact pinned `pymobiledevice3 v11.12.1` source describes `PreferredRsdTunnel` as the no-root wrapper for callers wanting a working iOS 17+ RSD path without choosing a concrete tunnel. On macOS it prefers Apple's native `remoted` path and falls back to the userspace tunnel; elsewhere it uses the userspace tunnel. Keep this wrapper unless observed hardware evidence disproves the assumption.

`AsyncExitStack` owns the complete stack. If an inner layer fails, already-entered resources unwind before an error escapes. No raw RSD host/port enters application state.

Set/clear are awaited directly:

```python
await location_service.set(latitude, longitude)
await location_service.clear()
```

### Developer Disk Image boundary

`DvtProvider` itself is not treated as proof that a Developer Disk Image is prepared. `pymobiledevice3` exposes a separate mounter/auto-mount path. GeoPortLocal does **not** pre-emptively add an Internet-dependent DDI download/mount step merely from assumption.

If the actual target phone fails to open DVT with evidence indicating a missing/unavailable developer image, local qualification must first reproduce and classify that exact failure. Only then may the adapter gain a narrow DDI preparation step, with tests and explicit offline implications.

## 6. Compatibility policy

Initial declared path:

```text
iOS >= 17.4  -> modern adapter
17.0-17.3.1  -> explicit unsupported result in this milestone
< 17          -> unsupported until a separate tested adapter is justified
```

Do not reintroduce legacy raw RSD tuple caching merely to broaden old-version support.

## 7. SessionManager ownership

One `SessionManager` owns:

```text
adapter
one asyncio mutation lock
current state
device descriptor
one DeviceConnection or None
current simulated Location or None
last safe GeoPortError or None
```

Discovery/connect/set/clear/disconnect and authoritative presence checks are serialized through the same lock. There is no per-operation thread creation or global terminate flag.

Timeouts:

```text
discovery      5 s
connect       20 s
set location  10 s
clear         10 s
disconnect     5 s
presence       2 s
```

Failure rules:

- failed connect caches no connection;
- non-transport set/clear failure restores the previous truthful state and records the safe error;
- `DEVICE_DISCONNECTED`, `TUNNEL_UNAVAILABLE` or `OPERATION_TIMEOUT` invalidates the owned session;
- explicit clear is permitted from both READY and SIMULATING and always awaits the device clear operation;
- disconnect is idempotent and still closes the connection if clear-on-disconnect fails;
- shutdown uses the same cleanup path.

A timeout is treated conservatively because device-side completion may be uncertain.

## 8. Idle disconnect detection

The browser polls `/api/device/status` about every 2.5 seconds only while a session exists. `SessionManager.check_presence()` owns the complete check under the same mutation lock as connection changes and bounds the probe to two seconds:

```text
identifier present -> preserve session
successful enumeration + absent -> invalidate session with DEVICE_DISCONNECTED
probe failed/timed out -> unknown; preserve potentially healthy session
```

When physical absence has already been positively established, invalidation does not attempt an impossible clear against the absent transport. It drops logical ownership, best-effort closes the stale connection, and requires a fresh connection after reattach.

Keeping probe + invalidation under one lock prevents a stale absence result from invalidating a newer connection created concurrently.

## 9. Canonical local API

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

`/api/health` performs no phone, fuel, map or Internet operation.

Expected project errors use stable JSON envelopes. Request-validation failures are sanitized. Any otherwise-unhandled application exception is converted to a generic `INTERNAL_ERROR` response; raw exception text/traceback is not returned to the browser. Normal handling logs only the exception class, not an arbitrary exception message.

## 10. Loopback listener and process coexistence

The launcher binds only to `127.0.0.1`.

No explicit `--port`:

1. atomically bind/listen on preferred 54321;
2. if unavailable, bind port 0 on loopback;
3. pass that already-bound socket to uvicorn;
4. log the actual URL;
5. optionally open the browser directly.

Explicit `--port N`: bind that loopback port or fail clearly.

GeoPortLocal never kills the existing port owner and never scans for processes named GeoPort. The already-listening socket removes the check-then-bind race. Browser launch needs no timer/helper thread; an early browser request can queue on the reserved listener until uvicorn accepts it.

## 11. Browser/local-control security boundary

Loopback binding is necessary but not sufficient for a browser-accessible local control plane. `runtime/security.py` adds a second boundary.

### Host validation

Requests must resolve through an allowed local Host (`127.0.0.1` or `localhost`; `testserver` exists for the test harness). Non-local Host values are rejected before application routes run, reducing DNS-rebinding exposure.

### Cross-site mutation protection

For mutating `/api/*` methods (`POST`, `PUT`, `PATCH`, `DELETE`):

- `Sec-Fetch-Site: cross-site` is rejected;
- when a browser `Origin` is present, scheme, hostname and effective port must exactly match the request origin;
- another localhost port is not accepted merely because its hostname is local;
- local non-browser clients without an Origin header remain usable.

A rejected mutation receives a stable `INVALID_REQUEST` response and must not alter device state.

### Content and cache policy

Responses carry a restrictive CSP:

```text
default-src 'self'
base-uri 'none'
object-src 'none'
frame-ancestors 'none'
form-action 'none'
script-src 'self'
style-src 'self'
font-src 'self'
connect-src 'self'
img-src 'self' https://tile.openstreetmap.org
```

This makes “no remote executable JavaScript” an enforced browser policy, not only a coding convention.

Additional response headers include:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

The referrer policy deliberately does not suppress the browser Referer for OpenStreetMap tile requests; only the local origin is sent cross-site, not a path/query. HTML and `/api/*` responses are `Cache-Control: no-store` so stale browser state is not treated as authoritative. Static package assets retain normal cache validators.

The page itself does not request browser geolocation; selected coordinates are explicit user input, map clicks or fuel-quote coordinates.

## 12. Fuel boundary

`ProjectZeroThreeProvider` is isolated because GeoPortLocal does not own its schema or uptime.

Implemented network policy:

```text
HTTPS with certificate verification
connect timeout   3 s
read timeout      5 s
maximum attempts  2
retry delay       0.5 s
retry transport/5xx only
no retry for 4xx/schema failures
```

Provider output is validated into normalized fuel records. `FuelService` serializes refreshes, reuses a successful snapshot for 60 seconds and may return last-good data explicitly marked stale.

Fuel failure cannot break health or device APIs.

## 13. Browser UI behavior

All executable assets come from the local package. The map uses only remote OSM image tiles.

Typical workflow:

```text
refresh devices
-> connect and wait for READY
-> optional explicit recovery Clear while READY
-> choose coordinates
-> set and wait for SIMULATING
-> clear and wait for READY
-> disconnect and wait for DISCONNECTED
```

Set and Clear are enabled only when a live session is in READY/SIMULATING as appropriate; Clear remains available in READY specifically for stale-simulation recovery. Selecting a fuel quote fills the coordinate picker but does not call the location mutation endpoint automatically.

If map tiles or the Internet fail, manual coordinates and every local device control remain available.

## 14. Logging/privacy

Normal logs use the same redacting formatter for console and persisted diagnostics.

Rules:

- shortened device suffix only when useful;
- common full modern/legacy UDID and labelled serial forms are redacted;
- pair records/auth material are never routine log content;
- exact selected latitude/longitude are not normal log content;
- blanket dependency DEBUG is not enabled by default;
- unexpected application errors do not log arbitrary exception messages at normal level.

The desktop build also attempts a bounded rotating per-user log. On macOS:

```text
~/Library/Logs/GeoPortLocal/geoportlocal.log
```

The primary log is capped at roughly 1 MB with two backups. Log-file creation failure must never prevent application startup. GeoPortLocal does not share a log/config path with the installed legacy app.

## 15. Packaging

Development targets Python 3.14. `uv.lock` is deliberately generated and verified on the target Mac rather than fabricated in GitHub-only work.

First Mac package:

```text
GeoPortLocal.app
bundle id: io.github.kkirang.geoportlocal
PyInstaller onedir/BUNDLE style
```

The spec includes local web assets and initially uses `collect_all("pymobiledevice3")` for reliability because the dependency has runtime-loaded pieces. Size pruning, signing/notarization distribution work and Windows packaging come after the primary correctness gate.

Persistent file logging is important for the windowed package because `console=False` means stderr is not a reliable user-facing diagnostic surface after freezing.

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
legacy CDN JS framework stack          -> local assets + restrictive CSP
```

## 17. Evidence boundary

The committed architecture and regression tests establish design intent and test coverage. They do not establish local PASS status.

Before regular use, the target Mac must still prove:

- generated lockfile and locked dependency resolution;
- Ruff/full pytest success;
- real USB/trust/Developer Mode path;
- actual `PreferredRsdTunnel`/DVT/LocationSimulation behavior;
- explicit recovery clear from READY;
- set/clear and repeated cycles;
- unplug/reconnect;
- CSP/origin/cache/browser behavior in the real browser;
- persistent packaged diagnostics;
- live provider compatibility;
- packaged app launch/shutdown/relaunch and side-by-side coexistence.

Those observations belong in `docs/TEST_MATRIX.md`. Repository inspection alone cannot mark them PASS.

# GeoPortLocal modernization master plan

Status: active planning baseline  
Date: 2026-09-10  
Active branch: `geoportlocal-modernization`  
Legacy baseline: `main`

## 1. Goal

Bring the forked GeoPort codebase forward to a maintainable 2026 implementation without discarding the parts that make it useful.

The target product remains **GeoPortLocal**. The modernization must run side-by-side with the existing downloaded GeoPort application on the Mac. The existing application is not uninstalled, overwritten, renamed, or used as the development target.

Success is not “more features.” Success is:

- current iPhone/iOS discovery and connection works reliably;
- setting a simulated location either succeeds demonstrably or returns a truthful failure;
- clearing simulation and disconnecting are deterministic;
- stale tunnels/sessions cannot be reused;
- repeated operations do not leak threads, tasks, ports or device state;
- fuel-price lookup remains useful but is isolated from the device runtime;
- the source tree can be installed, tested and packaged reproducibly;
- Codex/Astra can work on one subsystem without loading the entire legacy repository;
- the old working GeoPort remains available throughout development.

## 2. Current baseline and why it must change

The fork currently tracks the old upstream repository closely. The codebase is dominated by:

- one large `src/main.py` containing Flask routes, device discovery, pairing, developer mode, tunnel management, location simulation, process management, external API access, platform branching and application startup;
- two very large HTML templates containing substantial UI/CSS/JavaScript;
- global mutable state representing the selected device and connection;
- explicit thread management layered around asyncio calls;
- old `pymobiledevice3` tunnel orchestration;
- no project dependency manifest or lockfile;
- no regression test suite;
- no reproducible build configuration in the repository.

This architecture makes failures ambiguous. For example, a tunnel can fail to establish, the resulting `None` host/port can still enter the session map, and later requests can reuse that invalid entry. A web request may therefore claim the connection exists when the device transport is already invalid.

The modernization must remove that ambiguity rather than hide it behind retries.

## 3. Product boundary

### Keep

GeoPortLocal should retain these capabilities:

1. Discover a connected iPhone/iPad.
2. Show basic device metadata required to choose the device.
3. Establish the correct developer-service connection for supported iOS versions.
4. Set one simulated latitude/longitude.
5. Clear the simulated location.
6. Disconnect/close the session cleanly.
7. Display an interactive map for choosing a coordinate.
8. Display Australian fuel-price information through a provider abstraction.
9. Filter/select fuel type and region where the provider supports it.
10. Provide concise local diagnostics when a device operation fails.

### Remove or quarantine from the modern core

The first production-quality GeoPortLocal build will not depend on:

- GPX playback;
- route movement/interpolation;
- custom walking/driving speed;
- joystick/free-movement simulation;
- broad location-history or social-app features;
- remote GitHub broadcast messages;
- IP-based country detection;
- forced Wi-Fi enablement as a side effect of merely listing devices;
- third-party-service acceptance checks;
- anti-detection or account-management behavior.

Existing legacy code for these functions is not deleted at the start. It remains in `main` and can remain in a `legacy/` snapshot until the modern core has passed hardware tests. It simply does not constrain the new runtime architecture.

## 4. Explicit safety / third-party boundary

GeoPortLocal is responsible for the device-side simulation operation it performs. It is not responsible for making a third-party application accept a simulated location.

The project will not implement VPN/IP matching, device-fingerprint concealment, root/jailbreak hiding, account cycling, A01/A09 avoidance, or other measures whose purpose is to bypass a third party's anti-abuse or location-integrity controls.

This is also an engineering boundary: the UI must not conflate “location simulation was successfully requested on the device” with “a third-party application accepted the location.”

## 5. Supported platform strategy

### Primary development target

- macOS on Apple Silicon.
- Python 3.14.
- Current stable `pymobiledevice3` 11.x, pinned in the lockfile after compatibility verification.
- iOS 17.4+ as the clean modern transport baseline.
- iOS 18.x and iOS 26.x included in the hardware smoke matrix.

Why iOS 17.4+: current `pymobiledevice3` provides `PreferredRsdTunnel`, which chooses the best no-root developer-service transport. On macOS it can use Apple's native `remoted` path and fall back when required. That allows GeoPortLocal to stop manually owning TCP/QUIC RSD host/port tunnel state for the normal modern path.

### Secondary target

Windows support is retained as a product goal, but the Mac path is made correct first. The same device-controller API must support a Windows adapter test later without UI rewrites.

### Compatibility path

- iOS 17.0-17.3.1 requires a different privileged tunnel path in current `pymobiledevice3` and is not part of the first clean runtime path.
- iOS 16 and earlier may be supported by a legacy/lockdown adapter only if there is a real need and the cost is small.

Do not complicate every modern code path to preserve old iOS versions before the primary target is reliable.

## 6. Target architecture

The target dependency direction is:

```text
Browser UI
   |
HTTP/API layer
   |
Application services
   |----------------------|
DeviceController       FuelService
   |                      |
PymobiledeviceAdapter  FuelProvider
   |                      |
pymobiledevice3        ProjectZeroThree (initial)
```

The browser must never talk directly to `pymobiledevice3` concepts such as RSD addresses, pair records or tunnels.

The UI should consume a small application contract such as:

```text
GET  /api/devices
POST /api/device/connect
GET  /api/device/status
POST /api/location/set
POST /api/location/clear
POST /api/device/disconnect
GET  /api/fuel/prices
GET  /api/health
```

Exact endpoint naming can change during implementation, but the boundary cannot collapse back into one global `main.py`.

## 7. Device state model

One selected device is represented by one owned session.

```text
DISCONNECTED
    -> DISCOVERING
    -> DISCOVERED
    -> CONNECTING
    -> READY
    -> SIMULATING
    -> CLEARING
    -> READY
    -> DISCONNECTING
    -> DISCONNECTED
```

Any transport-level failure from `CONNECTING`, `READY`, `SIMULATING` or `CLEARING` transitions the session to `ERROR`, closes owned resources, and then to `DISCONNECTED` after cleanup.

There is no valid state in which a session with a missing/failed service provider is cached as READY.

The application exposes state, not implementation details. A caller receives an explicit error code/category such as:

- `DEVICE_NOT_FOUND`
- `DEVICE_NOT_TRUSTED`
- `DEVELOPER_MODE_REQUIRED`
- `TUNNEL_UNAVAILABLE`
- `DEVICE_DISCONNECTED`
- `LOCATION_SET_FAILED`
- `LOCATION_CLEAR_FAILED`
- `OPERATION_TIMEOUT`

Raw exception strings can be placed in debug logs, not treated as the API contract.

## 8. Implementation sequence

### Phase 0 — preserve the legacy baseline

Already established:

- leave `main` unchanged as the legacy reference;
- use `geoportlocal-modernization` for modernization work;
- keep the existing downloaded GeoPort app installed locally;
- new packaged application name is `GeoPortLocal.app`, not `GeoPort.app`;
- do not publish a GitHub Release until hardware gates are passed.

Exit gate: no modernization work modifies the existing installed app or requires deleting the old app.

### Phase 1 — make the source reproducible

Create:

- `pyproject.toml`;
- `uv.lock`;
- `.python-version` set to Python 3.14;
- development extras for pytest, pytest-asyncio, Ruff and packaging;
- a minimal application package under `src/geoportlocal/`;
- a deterministic entry point;
- a pinned PyInstaller configuration/spec after the source build works.

Initial dependency policy:

- pin the tested `pymobiledevice3` version rather than `>=` floating major behavior;
- use the stable PyInstaller release current at implementation time, never an old privileged build with known security issues;
- do not add a frontend framework merely to modernize the UI.

Exit gate:

```text
uv sync
uv run python -m geoportlocal --help
uv run pytest
```

works from a clean clone on the development Mac.

### Phase 2 — build the device adapter before the web UI

Create a small protocol/interface for device operations and implement it using current public `pymobiledevice3` APIs.

For modern iOS developer/DVT services:

- obtain the RSD provider with `PreferredRsdTunnel`;
- open `DvtProvider` as an async context manager;
- open `LocationSimulation` as an async context manager;
- `await set(latitude, longitude)`;
- `await clear()`;
- guarantee cleanup through context-manager ownership.

Do not port these legacy concepts into the new adapter unless current upstream explicitly requires them:

- global `rsd_host`;
- global `rsd_port`;
- manually cached tunnel address tuples;
- `stop_remoted_if_required()` from application code;
- direct `CoreDeviceTunnelProxy` orchestration for the normal macOS path;
- imports from `pymobiledevice3.cli.*`.

Use fake adapters for unit tests so most test runs require no iPhone.

Exit gate: adapter unit tests prove successful and failed connect/set/clear/disconnect transitions without Flask or a browser.

### Phase 3 — implement SessionManager

Create exactly one owner for device lifetime.

Responsibilities:

- selected device identity;
- current state;
- current provider/session resources;
- operation lock to serialize mutating operations;
- timeout enforcement;
- cancellation;
- resource cleanup;
- session invalidation after disconnect/failure.

No request handler stores connection globals.

Exit gate: the entire state-transition matrix passes with a fake adapter, including unplug/failure simulation and 100 repeated connect/disconnect cycles.

### Phase 4 — thin local API

Extract HTTP routes from the device implementation.

Requirements:

- bind `127.0.0.1` only;
- debug mode off by default;
- request validation for coordinates and identifiers;
- consistent JSON error envelope;
- API operations await actual device operations before returning success;
- device API remains available when all optional Internet services are offline.

The current Flask UI may initially call the new backend to reduce migration risk. Framework replacement is not a goal.

Exit gate: API contract tests with the fake adapter pass without a connected phone.

### Phase 5 — fuel provider isolation

Create `FuelProvider` and an initial `ProjectZeroThreeProvider`.

Requirements:

- HTTPS verification enabled;
- explicit connect/read timeout;
- bounded retry only for safe idempotent reads;
- schema validation/normalization before data reaches the UI;
- timestamp/freshness recorded when available;
- last-good cache allowed, but clearly marked stale;
- provider outage cannot affect device discovery or location controls.

Do not hard-code provider response details throughout JavaScript or device code.

Exit gate: malformed JSON, provider timeout, provider HTTP errors and empty region results all produce deterministic UI/API states.

### Phase 6 — simplify the UI without feature churn

Retain the familiar workflow:

1. pick device;
2. connect;
3. choose/search coordinate or fuel price marker;
4. simulate location;
5. clear location;
6. disconnect/exit.

Remove duplicate Bootstrap versions, obsolete jQuery where unnecessary, duplicate templates and unused route/GPX controls from the modern page.

The UI must show the actual backend state. Buttons derive from state instead of local guesses.

Exit gate: UI cannot display `READY` or `SIMULATING` when backend state is not the corresponding state.

### Phase 7 — packaging and side-by-side installation

Package as:

- display name: `GeoPortLocal`;
- macOS bundle: `GeoPortLocal.app`;
- bundle identifier: `io.github.kkirang.geoportlocal` unless signing/notarization requirements require adjustment;
- separate preferences/cache/log path under the GeoPortLocal name.

Do not reuse the old GeoPort application bundle or overwrite `/Applications/GeoPort*.app`.

First package as `onedir`/app bundle while debugging. Optimize size only after correctness; one-file packaging is not an acceptance criterion.

Exit gate: old GeoPort and GeoPortLocal can both exist on the same Mac, one can be closed and the other launched without shared-process/port cleanup code killing the other.

### Phase 8 — hardware qualification

At minimum test:

- cold launch with phone disconnected;
- USB attach after launch;
- already-attached USB launch;
- trust/pairing not complete;
- developer mode unavailable/disabled;
- successful connect;
- set location;
- clear location;
- clear twice;
- set/clear 20 times;
- disconnect while READY;
- unplug while READY;
- unplug while SIMULATING;
- reconnect after unplug;
- close application while READY;
- close application while SIMULATING;
- port 54321 already occupied;
- Internet unavailable;
- fuel provider unavailable;
- iOS 18.x device if available;
- iOS 26.x device if available.

Record actual device/iOS/macOS/version results in `docs/TEST_MATRIX.md` rather than relying on “works for me.”

Exit gate: no known P0/P1 lifecycle defect and no false-success result in the supported hardware matrix.

## 9. Work packages for agents

The work should be split into bounded changes. One agent turn should normally own one package:

1. Bootstrap project metadata and empty package without changing legacy runtime.
2. Define state and domain errors.
3. Create adapter protocol + fake adapter tests.
4. Implement current `pymobiledevice3` discovery/connect adapter.
5. Implement set/clear through DVT location simulation.
6. Implement SessionManager and failure handling.
7. Add thin API over fake adapter.
8. Connect API to real adapter.
9. Extract fuel provider.
10. Migrate minimal UI workflow.
11. Add packaging.
12. Run local hardware qualification and fix observed defects.

Do not ask Astra/Codex to “modernize the whole repo.” That forces it to read the largest files, encourages unrelated changes and consumes far more agent allowance.

## 10. Definition of done

GeoPortLocal modernization is ready for regular use when all of these are true:

- clean clone installs reproducibly;
- dependency versions are locked;
- source runs without admin/root on the primary macOS + iOS 17.4+ path;
- no application code imports `pymobiledevice3.cli.*`;
- no global host/port/session state is used by request handlers;
- connection state is represented by one tested manager;
- no invalid session can be cached;
- set/clear responses correspond to completed device operations;
- repeated operations do not accumulate tasks/threads/processes;
- shutdown releases owned resources;
- local server binds loopback only;
- TLS verification is enabled;
- fuel-provider failure is isolated;
- old GeoPort remains installable/runnable side-by-side;
- the required hardware smoke matrix has recorded results;
- remaining limitations are documented precisely.

Until then, the existing downloaded GeoPort remains the operational fallback.
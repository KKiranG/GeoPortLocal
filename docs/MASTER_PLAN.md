# GeoPortLocal modernization master plan

Status: implementation baseline complete; local qualification pending  
Date: 2026-09-10  
Active branch: `geoportlocal-modernization`  
Legacy baseline: `main`

## 1. Goal

Modernize the forked GeoPort codebase into a small, maintainable local application without sacrificing the useful core workflow or disturbing the existing working GeoPort installation.

Success means:

- current iPhone discovery and developer-service connection are reliable on the declared supported Mac/iOS matrix;
- location set/clear either complete successfully or fail truthfully;
- stale sessions cannot be reused;
- unplug/reconnect creates a fresh session without restarting GeoPortLocal;
- repeated operations do not accumulate tasks, threads, ports or device state;
- fuel-price lookup is isolated from device control;
- source and packaged app are reproducible;
- legacy GeoPort remains available as the fallback until qualification is complete.

The implementation needed to exercise those gates now exists on this branch. The remaining work is evidence gathering and narrow fixes revealed by local execution, not another broad redesign.

## 2. Product boundary

The modern core keeps:

1. iPhone/iPad discovery and basic metadata.
2. Trust/developer-mode diagnostics.
3. Current iOS developer-service connection for the supported version range.
4. One simulated latitude/longitude.
5. Clear simulation.
6. Deterministic disconnect/reconnect.
7. Coordinate entry and map picking.
8. Australian fuel region/type/quote selection through a provider boundary.
9. Concise local diagnostics.

The modern core intentionally excludes GPX playback, route interpolation, walking/driving speed, joystick movement, broad location-history/social features, GitHub broadcast messages, IP-country detection, forced Wi-Fi changes, account automation and third-party anti-abuse/location-integrity evasion.

Legacy implementations of excluded features remain available on `main` as reference. They are not copied into the modern runtime merely for compatibility.

## 3. Safety and third-party boundary

GeoPortLocal is responsible only for the device-side simulation request it performs. A successful simulation operation is not proof that a third-party application accepts the resulting device location.

The project does not implement VPN/IP matching, fingerprint concealment, root/jailbreak hiding, account cycling, geofence bypass, A01/A09 avoidance or related measures whose purpose is to defeat a third party's integrity or anti-abuse controls.

## 4. Supported platform strategy

Primary qualification target:

- macOS on Apple Silicon;
- Python 3.14;
- `pymobiledevice3==11.12.1` as the current audited dependency baseline;
- iOS 17.4+ modern path;
- actual iOS 18.x/26.x support recorded only when hardware is tested.

The modern device path is:

```text
PreferredRsdTunnel
-> DvtProvider
-> LocationSimulation
```

GeoPortLocal does not own or cache raw RSD host/port tuples in application state.

Windows remains a later product target. It does not block the first private Mac alpha.

## 5. Implemented architecture

Dependency direction:

```text
local browser UI
      |
FastAPI routes
      |
SessionManager -------- FuelService
      |                    |
DeviceAdapter           FuelProvider
      |                    |
pymobiledevice3         Project Zero Three
```

The browser and API do not import `pymobiledevice3` concepts. Device-specific dependency code is isolated under `src/geoportlocal/device/`.

The browser UI uses local HTML/CSS/JavaScript. Its coordinate map is a project-owned Web-Mercator tile renderer. Remote map content is image tiles only; there is no remotely loaded executable JavaScript. If map tiles or the Internet are unavailable, direct coordinates and local device control remain usable.

One `SessionManager` owns the selected device connection, authoritative state, current simulated coordinate, mutation lock, timeouts and cleanup.

## 6. Canonical API contract

The implemented local API is:

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
```

Mutation success is returned only after the underlying operation completes. Failures use stable, sanitized error envelopes rather than HTTP 200 with an error string.

The UI derives displayed state and enabled actions from server snapshots; JavaScript does not invent `READY` or `SIMULATING` because a button was clicked.

## 7. Device lifecycle

Authoritative states currently include:

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

Normal flow:

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

Transport-level failure invalidates the owned session and returns to `DISCONNECTED` after cleanup. Recovery establishes a fresh dependency stack rather than reusing stale transport state.

While a session exists, `/api/device/status` performs a cheap `usbmux` presence probe. Only a successful enumeration proving the selected identifier absent is authoritative enough to invalidate idle state; a failed probe is treated as unknown rather than destroying a potentially healthy session.

## 8. Port and process ownership

GeoPortLocal binds loopback only.

Startup atomically reserves the listening socket before uvicorn runs:

- explicit `--port N`: bind that loopback port or fail clearly if unavailable;
- no `--port`: prefer 54321, otherwise request an OS-assigned free loopback port.

GeoPortLocal never kills the existing port owner and never scans/kills processes by a `GeoPort` name match. The reserved socket is passed directly to uvicorn, avoiding the check-then-bind race.

The browser is opened directly after the socket is listening; no helper/background browser-launch thread is used.

## 9. Fuel isolation

`FuelService` owns provider access and an in-memory last-good cache. `ProjectZeroThreeProvider` currently uses:

```text
connect timeout: 3 s
read timeout:    5 s
attempts:        2 total
retry delay:     0.5 s
```

Retries are limited to safe read failures such as transport/5xx conditions. TLS verification remains enabled. Provider responses are normalized and validated before reaching the UI.

A provider outage must not affect `/api/health`, device discovery or device mutations. Last-good data may be returned as explicitly stale when available.

## 10. Logging and privacy

Normal logging is intentionally small and diagnostic:

- lifecycle/state outcomes and durations where useful;
- shortened device suffix only when identification is necessary;
- no full UDIDs/pair records/auth material;
- no selected latitude/longitude in normal logs;
- process-wide formatter redacts common full iOS identifier patterns from dependency messages and tracebacks.

Do not enable blanket dependency DEBUG logging for ordinary use.

## 11. Packaging

The first Mac package is deliberately conservative:

```text
GeoPortLocal.app
bundle id: io.github.kkirang.geoportlocal
PyInstaller onedir/BUNDLE style
```

The app has its own name and bundle identifier and must not overwrite or rename the existing GeoPort application. Bundle-size optimization, signing/notarization distribution work and Windows packaging come after correctness.

## 12. Completed implementation phases

Implemented on `geoportlocal-modernization`:

- project metadata and Python 3.14 baseline;
- domain/device/fuel contracts;
- modern `pymobiledevice3` adapter;
- serialized `SessionManager`;
- thin local API and sanitized errors;
- presence probing for idle unplug detection;
- isolated fuel provider/cache;
- modern browser UI and map/fuel workflow;
- safe loopback port ownership;
- identifier-redacting logging;
- macOS PyInstaller spec and bootstrap/check/build scripts;
- fake-adapter/session/API/fuel/logging/adapter contract tests;
- Codex/local qualification handoff docs.

No claim above means the real Mac/iPhone path has passed. Repository inspection proves structure and test intent, not hardware compatibility.

## 13. Remaining gates

### Gate A — local reproducibility

On the target Mac:

```text
uv lock
uv sync --locked
uv run ruff check .
uv run pytest
```

Commit the generated `uv.lock` plus only genuine fixes revealed by this gate. Do not hand-edit the lockfile or opportunistically upgrade dependencies.

### Gate B — source-app hardware qualification

Run the ordered Mac/iPhone matrix in `docs/LOCAL_BOOTSTRAP.md` and record only observed results in `docs/TEST_MATRIX.md`:

- no-phone launch;
- USB attach/discovery;
- trust/developer-mode errors;
- successful connect;
- set/clear;
- repeated set/clear;
- unplug while READY;
- reconnect;
- unplug while SIMULATING;
- reconnect;
- shutdown/relaunch;
- provider/offline degradation.

### Gate C — packaged app

Only after Gate B passes:

```bash
bash scripts/build_macos.sh
```

Qualify `dist/GeoPortLocal.app` independently for dynamic imports/data files, launch/relaunch, actual device workflow, shutdown and side-by-side coexistence.

### Gate D — release decision

A private regular-use alpha requires:

- clean locked dependency resolution;
- fast suite passing;
- zero known P0/P1 lifecycle defects in the declared primary hardware matrix;
- no false success;
- no stale session after unplug/reconnect;
- legacy GeoPort preserved side-by-side;
- limitations recorded precisely.

Do not publish a GitHub Release before these gates pass.

## 14. Agent/model allocation

The implementation phase no longer warrants broad autonomous exploration.

Use ordinary Codex for mechanical work such as lock generation, Ruff, pytest and straightforward failures. Reserve GPT-6 Astra for difficult real-device/tunnel diagnosis or architecture-sensitive fixes where the additional reasoning is justified. Current OpenAI guidance notes that Astra can consume Codex allowance faster than GPT-5.6 Sol, so spending it on deterministic mechanical gates is wasteful.

For exact bounded prompts, use `docs/CODEX_HANDOFF.md`.

## 15. Definition of done

GeoPortLocal is ready to replace the old application for the declared primary use case only when all of these are evidenced:

- clean clone installs reproducibly from committed lock data;
- source checks pass;
- real supported iPhone discovers/connects/sets/clears reliably;
- repeated cycles do not show progressive resource growth;
- unplug/reconnect does not leave a stale logical session;
- shutdown releases owned resources;
- device workflow remains functional when optional Internet services fail;
- packaged app passes the same core workflow;
- old GeoPort remains independently usable;
- no remaining P0/P1 is hidden by retries or optimistic UI state.

Until then, the existing downloaded GeoPort remains the operational fallback.

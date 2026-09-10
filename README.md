# GeoPortLocal

GeoPortLocal is a modernization fork of GeoPort focused on a small, reliable local workflow: connect an iOS device, choose a coordinate, set/clear iOS location simulation, and optionally view Australian fuel-price coordinates.

The active modernization branch is `geoportlocal-modernization`. The legacy `main` branch remains the upstream-derived fallback and has not been rewritten. No modernization release has been published.

## Current status

The hardware-independent implementation is in place. It includes:

- Python 3.14 project metadata for `uv`;
- a FastAPI/uvicorn loopback-only runtime;
- a project-owned device adapter over current `pymobiledevice3` APIs;
- one deterministic `SessionManager` for connect/set/clear/disconnect state;
- the current iOS 17.4+ path using `PreferredRsdTunnel -> DvtProvider -> LocationSimulation`;
- typed API errors and coordinate validation;
- idle device-presence probing without a background thread;
- a Project Zero Three fuel provider behind a validated/cacheable boundary;
- a plain HTML/CSS/JavaScript browser UI with optional Leaflet map;
- identifier-redacting logs;
- automatic loopback port fallback when 54321 is already occupied;
- fake-adapter regression tests;
- a first macOS `GeoPortLocal.app` PyInstaller specification.

The real iPhone path and packaged `.app` still require qualification on the target Mac before this branch should replace the old application for regular use.

## Design rules

GeoPortLocal follows several non-negotiable runtime invariants:

1. A location operation is not reported successful until the underlying device call completes.
2. Failed or incomplete sessions are never cached as reusable connections.
3. One selected device has one owned session and serialized mutating operations.
4. Transport failure invalidates the session; recovery creates a fresh one.
5. Device control does not depend on fuel-price, map-tile, GitHub, IP-geolocation or other unrelated Internet services.
6. The local HTTP server binds to `127.0.0.1` only.
7. TLS verification is not disabled.
8. Normal logs redact full iOS identifiers.
9. Application code does not import `pymobiledevice3.cli.*` internals.
10. The existing GeoPort application is never killed or overwritten by GeoPortLocal.

See `AGENTS.md` for the agent contract and `docs/ARCHITECTURE.md` for the runtime design.

## Scope

The modern core intentionally keeps:

- iOS device discovery and selection;
- trust/developer-mode diagnostics;
- location set/clear;
- deterministic disconnect/reconnect;
- coordinate entry and map picking;
- Australian fuel-region/type/quote selection.

It intentionally does not rebuild GPX playback, route movement, joystick simulation, arbitrary walking/driving automation, broadcast/referral messages, IP-country detection, or forced Wi-Fi side effects.

GeoPortLocal reports whether its own iOS simulation operation completed. It does not claim that a third-party application will accept a simulated location, and this project does not implement VPN/IP matching, fingerprint concealment, account cycling, jailbreak/root hiding, geofence bypass or third-party anti-abuse evasion.

## First local bootstrap

Keep your existing GeoPort installation in place. In the GeoPortLocal clone:

```bash
git fetch origin
git switch geoportlocal-modernization
git pull --ff-only
bash scripts/bootstrap_macos.sh
```

That first local bootstrap creates `uv.lock`, syncs the Python 3.14 environment, runs Ruff and runs the fast test suite.

After `uv.lock` has been reviewed and committed, the ordinary quality gate is:

```bash
bash scripts/check.sh
```

Run the source app with:

```bash
uv run geoportlocal
```

The application prefers `http://127.0.0.1:54321`. If that port belongs to the existing GeoPort app or any other process, GeoPortLocal leaves it alone and automatically selects another free loopback port. The actual URL is printed at startup.

For the exact first Mac/iPhone procedure, use `docs/LOCAL_BOOTSTRAP.md`.

## Browser workflow

The modern UI is intentionally narrow:

```text
Refresh device
-> Connect
-> enter/click/select coordinates
-> Set location
-> Clear location
-> Disconnect
```

Fuel-price lookup is optional. Selecting a fuel quote fills the coordinate picker; it does not automatically apply a location to the device.

The map is also optional. If Leaflet or map tiles cannot load, direct coordinate entry and all device API operations remain available.

## Packaging

After the source application passes the actual Mac/iPhone qualification:

```bash
bash scripts/build_macos.sh
```

The expected first bundle is:

```text
dist/GeoPortLocal.app
```

Bundle identifier:

```text
io.github.kkirang.geoportlocal
```

Do not replace or rename the existing `GeoPort.app` during qualification. Bundle size is deliberately not optimized before correctness is proven.

## Agentic development

This repository is structured to avoid wasting Codex/Astra context on the legacy monolith.

Start with `AGENTS.md`. Then open only the relevant document and target files:

- `docs/WORKLOG.md` — current handoff state;
- `docs/LOCAL_BOOTSTRAP.md` — exact local and hardware procedure;
- `docs/CODEX_HANDOFF.md` — bounded Astra/Codex sessions;
- `docs/MASTER_PLAN.md` — product sequence and acceptance gates;
- `docs/ARCHITECTURE.md` — runtime contracts;
- `docs/TEST_MATRIX.md` — regressions and hardware evidence;
- `docs/RESEARCH_2026-09.md` — external research baseline.

Do not begin a normal coding task by reading all of `src/main.py`, both legacy map templates, all research and Git history.

## Attribution and license

GeoPortLocal is forked from Dave Scroggie's `davesc63/GeoPort` project and retains the repository's GPL-3.0 license and upstream history. The modernization also depends on the `doronz88/pymobiledevice3` project.

The legacy branch remains available as the reference for upstream behavior while the new implementation is qualified independently.

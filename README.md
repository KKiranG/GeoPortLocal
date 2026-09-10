# GeoPortLocal

GeoPortLocal is a modernization fork of GeoPort focused on one reliable local workflow: discover an iOS device, connect, choose a coordinate, set or clear iOS location simulation, and optionally use Australian fuel-price coordinates.

The active branch is `geoportlocal-modernization`. Legacy `main` remains the upstream-derived fallback and has not been rewritten. No modernization release should be published until the local Mac/iPhone qualification gates pass.

## Current status

The hardware-independent implementation is in place:

- Python 3.14 project metadata for `uv`;
- FastAPI/uvicorn loopback-only runtime;
- project-owned `pymobiledevice3` adapter;
- one serialized `SessionManager` for connect/set/clear/disconnect state;
- iOS 17.4+ path using `PreferredRsdTunnel -> DvtProvider -> LocationSimulation`;
- typed API errors and strict coordinate validation;
- idle device-presence probing without a resident watcher thread;
- Project Zero Three fuel provider behind a validated, cacheable boundary;
- local HTML/CSS/JavaScript UI;
- project-owned Web-Mercator map picker using remote image tiles only, with no remote executable JavaScript;
- identifier-redacting logs;
- automatic loopback port fallback when 54321 is already occupied;
- fake-adapter/session/API/fuel/startup/logging/adapter-contract tests;
- conservative macOS `GeoPortLocal.app` PyInstaller specification.

The real iPhone path, live fuel payload and packaged `.app` still require qualification on the target Mac before this branch should replace the old application for regular use.

## Runtime invariants

1. A location operation is not reported successful until the underlying device call completes.
2. Failed or incomplete sessions are never cached as reusable connections.
3. One selected device has one owned session and serialized mutating operations.
4. Transport failure invalidates the session; recovery creates a fresh one.
5. Device control does not depend on fuel-price, map-tile, GitHub, IP-geolocation or other unrelated Internet services.
6. The local HTTP server binds to `127.0.0.1` only.
7. TLS verification is not disabled.
8. Normal logs redact full iOS identifiers and do not log selected coordinates.
9. Application code does not import `pymobiledevice3.cli.*` internals.
10. GeoPortLocal never kills, overwrites or renames the existing GeoPort application.
11. No per-operation or browser-launch helper thread is used by the modern runtime.

See `AGENTS.md` for the agent contract and `docs/ARCHITECTURE.md` for the implemented runtime design.

## Scope

The modern core intentionally keeps:

- iOS discovery and device selection;
- trust/developer-mode diagnostics;
- location set/clear;
- deterministic disconnect/reconnect;
- coordinate entry and local map picking;
- Australian fuel-region/type/quote selection.

It intentionally does not rebuild GPX playback, route movement, joystick simulation, arbitrary walking/driving automation, broadcast/referral messages, IP-country detection or forced Wi-Fi side effects.

GeoPortLocal reports whether its own iOS simulation operation completed. It does not claim that a third-party application will accept a simulated location, and it does not implement VPN/IP matching, fingerprint concealment, account cycling, jailbreak/root hiding, geofence bypass or third-party anti-abuse evasion.

## First local bootstrap

Keep the existing GeoPort installation in place. In the GeoPortLocal clone:

```bash
git fetch origin
git switch geoportlocal-modernization
git pull --ff-only
bash scripts/bootstrap_macos.sh
```

The first bootstrap creates `uv.lock`, syncs the Python 3.14 environment, runs Ruff and runs the complete fast pytest suite. Review and commit the generated lockfile before changing dependency versions.

After that, the ordinary quality gate is:

```bash
bash scripts/check.sh
```

Run the source app with:

```bash
uv run geoportlocal
```

GeoPortLocal prefers `http://127.0.0.1:54321`. If that port belongs to legacy GeoPort or another process, it leaves the owner untouched and reserves another free loopback port. The actual URL is logged at startup.

Use `docs/LOCAL_BOOTSTRAP.md` for the exact Mac/iPhone procedure.

## Browser workflow

```text
Refresh devices
-> Connect
-> enter/click/select coordinates
-> Set location
-> Clear location
-> Disconnect
```

Fuel lookup is optional. Selecting a fuel quote fills the coordinate picker; it does not automatically apply the location to the phone.

The map is optional. Only map image tiles are remote. If tile loading or the Internet fails, direct coordinate entry and all local device operations remain available.

## Packaging

After the source application passes the actual Mac/iPhone qualification:

```bash
bash scripts/build_macos.sh
```

Expected first bundle:

```text
dist/GeoPortLocal.app
```

Bundle identifier:

```text
io.github.kkirang.geoportlocal
```

Do not replace or rename the existing `GeoPort.app` during qualification. Bundle-size optimization is deliberately deferred until correctness is proven.

## Agentic development

The implementation stage is substantially complete. Do not restart a broad modernization review.

For the next local work, start with:

- `AGENTS.md` — invariants and scope;
- `docs/WORKLOG.md` — current state;
- `docs/CODEX_HANDOFF.md` — bounded local sessions;
- `docs/LOCAL_BOOTSTRAP.md` — exact local/hardware procedure.

Use the larger design documents only when a concrete failure requires them:

- `docs/MASTER_PLAN.md` — qualification/release gates;
- `docs/ARCHITECTURE.md` — runtime contracts;
- `docs/TEST_MATRIX.md` — automated and hardware regressions;
- `docs/RESEARCH_2026-09.md` — external assumptions.

Do not begin a normal task by reading all of legacy `src/main.py`, both old map templates, the whole research note and Git history.

The mechanical environment/lock/lint/test gate does not need GPT-6 Astra. Reserve Astra for difficult real-device/tunnel diagnosis or architecture-sensitive fixes where the extra reasoning is justified.

## Attribution and license

GeoPortLocal is forked from Dave Scroggie's `davesc63/GeoPort` project and retains the repository's GPL-3.0 license and upstream history. The modernization depends on `doronz88/pymobiledevice3`.

Legacy `main` remains available as the reference/fallback while the new implementation is qualified independently.

# GeoPortLocal local bootstrap and qualification

Date: 2026-09-10  
Target: macOS Apple Silicon first  
Branch: `geoportlocal-modernization`

This is the first point in the modernization where a local Mac is required. The existing downloaded GeoPort application is the fallback and must remain installed and untouched.

## 1. Preconditions

- Work from the GeoPortLocal clone, not the existing installed GeoPort app.
- Do not copy anything into `/Applications` yet.
- Do not delete, rename, terminate or modify the existing GeoPort app as part of bootstrap.
- A USB-connected iPhone is not required for dependency installation or the fast test suite.
- A real iPhone is required only for the hardware qualification section below.

The repository targets Python 3.14 and uses `uv`. `pymobiledevice3` is pinned in `pyproject.toml`; do not float it during initial qualification.

## 2. Sync exactly once

From the existing GeoPortLocal clone:

```bash
git fetch origin
git switch geoportlocal-modernization
git pull --ff-only
git status --short
```

The working tree should be clean before bootstrap. If it is not, stop and inspect the local changes rather than overwriting them.

Verify the branch:

```bash
git branch --show-current
```

Expected:

```text
geoportlocal-modernization
```

## 3. Create the reproducible environment

Verify `uv` first:

```bash
uv --version
```

If `uv` is not installed, install it using the current official Astral `uv` installation instructions. Do not add a repository-specific curl installer or Homebrew dependency just for GeoPortLocal.

Then run:

```bash
bash scripts/bootstrap_macos.sh
```

The script performs, in order:

```text
install/select Python 3.14 through uv
create uv.lock
sync exactly from that lock
run Ruff
run the complete fast pytest suite
```

After it succeeds:

```bash
git status --short
```

The expected new tracked artifact is `uv.lock`. Review and commit that lockfile before making dependency changes. Do not hand-edit it.

From then on, the ordinary quality gate is:

```bash
bash scripts/check.sh
```

It refuses to proceed without `uv.lock` and uses `uv sync --locked`, so dependency drift becomes visible instead of silent.

## 4. Start the source application

Run:

```bash
uv run geoportlocal
```

Expected startup properties:

- the server binds only to `127.0.0.1`;
- it prefers port `54321`;
- if `54321` is already occupied, GeoPortLocal does not kill that process and instead reserves another free loopback port;
- the actual URL is printed to the log;
- the browser opens automatically;
- `--no-browser` disables browser launch;
- an explicit busy `--port` fails clearly rather than silently choosing another port.

Examples:

```bash
uv run geoportlocal --no-browser
uv run geoportlocal --port 58424
```

The landing page must load even with no iPhone and with the Internet disconnected. The map and fuel-price panel may degrade when offline; device controls and `/api/health` must remain available.

## 5. First real-iPhone qualification

Use an iPhone running iOS 17.4 or newer. The first target is the user's current Mac/iPhone combination; do not broaden compatibility before this works reliably.

Record the Mac model/macOS version, iPhone model/iOS version and the committed `pymobiledevice3` version in `docs/TEST_MATRIX.md`.

Run these in order, stopping at the first failure:

1. Launch GeoPortLocal with no phone connected. Confirm the page loads and reports no device.
2. Attach the unlocked iPhone over USB. Press **Refresh**. Confirm one deterministic device row appears.
3. Press **Connect**. If iOS asks for Trust, approve it. Developer Mode must already be enabled; GeoPortLocal does not try to weaken the passcode or force-enable Developer Mode.
4. Confirm server state becomes `READY` only after the connection completes.
5. Choose an easily verifiable test coordinate that is appropriate for your own testing and press **Set location**.
6. Independently verify on the phone that the system-reported location changed. Do not use a third-party application's acceptance result as the GeoPortLocal verification oracle.
7. Press **Clear location** and independently verify that the phone returns to its real location.
8. Repeat set/clear 20 times without restarting GeoPortLocal.
9. While `READY`, unplug the USB cable. Within a few seconds the UI should invalidate the session rather than remain `READY` indefinitely.
10. Reconnect the phone and establish a fresh session without restarting the application.
11. While `SIMULATING`, unplug the phone. Confirm the next status/operation invalidates the session and that reconnect creates a fresh session.
12. Quit GeoPortLocal while `READY`, relaunch it and reconnect.
13. Quit GeoPortLocal while `SIMULATING`, then verify the phone's actual location state and record the observation. This case is hardware-dependent and must not be guessed from unit tests.

If any operation fails, capture only the smallest useful redacted log section. Do not paste pair records, full UDIDs or unrelated system logs into an agent prompt.

## 6. Fuel and offline qualification

Device correctness is independent of fuel data.

With GeoPortLocal running:

1. Load the fuel region/type panel and confirm a quote is normalized into price, suburb/state and coordinates.
2. Select a quote and confirm it fills the coordinate picker but does **not** automatically apply the location to the phone.
3. Disconnect the Mac from the Internet.
4. Confirm `/api/health`, device discovery, connect/set/clear for an already supported local device path, and direct coordinate entry remain usable.
5. Confirm the fuel panel reports unavailable or stale data without breaking device controls.

Project Zero Three is an external provider and its live schema/availability remains a qualification dependency, not an application invariant.

## 7. Build the first side-by-side Mac bundle

Only after the source build and hardware workflow are acceptable:

```bash
bash scripts/build_macos.sh
```

The script runs the locked sync, lint and test suite before invoking PyInstaller. Expected output:

```text
dist/GeoPortLocal.app
```

The bundle identifier is:

```text
io.github.kkirang.geoportlocal
```

Do not rename it to `GeoPort.app`. Do not copy it over the old application. For initial qualification, launch the generated bundle directly from `dist/GeoPortLocal.app`.

Test the packaged application separately because freezing can expose dynamic-import, data-file, codesigning and macOS process-lifecycle problems that do not exist in `uv run`.

## 8. What is intentionally not verified in GitHub-only work

The following claims require the local run and must remain marked unverified until observed:

- Python 3.14 dependency resolution on the user's Mac and the generated `uv.lock`;
- real USB pairing/trust behavior;
- `PreferredRsdTunnel` on the user's macOS/iOS combination;
- DVT `LocationSimulation.set()` and `.clear()` against the real phone;
- unplug/reconnect behavior of the real dependency stack;
- live Project Zero Three response compatibility;
- PyInstaller's complete `pymobiledevice3` frozen dependency set on Apple Silicon;
- the packaged app's shutdown behavior and macOS Gatekeeper/signing experience.

Do not mark a hardware row PASS from unit tests or from another user's report.

## 9. Recovery rule

If the modernization is unusable at any point, leave the old application alone and return to the legacy Git branch for reference:

```bash
git switch main
```

That does not uninstall or change the existing GeoPort application. The modernization branch is intentionally independent until its hardware gates pass.

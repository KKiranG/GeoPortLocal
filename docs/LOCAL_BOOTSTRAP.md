# GeoPortLocal local bootstrap and qualification

Date: 2026-09-10  
Target: macOS Apple Silicon first  
Branch: `geoportlocal-modernization`

This is the first point where the modernization requires the target Mac. Keep the existing downloaded GeoPort application installed and untouched as the fallback.

## 1. Preconditions

- Work from the GeoPortLocal clone, not the installed legacy app.
- Do not copy anything into `/Applications` yet.
- Do not delete, rename, terminate or modify existing GeoPort during bootstrap.
- A phone is not required for dependency installation or the fast test suite.
- Use a real iPhone only after the locked fast gate succeeds.
- Do not float the pinned `pymobiledevice3` version during initial qualification.

## 2. Sync once

```bash
git fetch origin
git switch geoportlocal-modernization
git pull --ff-only
git status --short
git branch --show-current
```

Expected branch:

```text
geoportlocal-modernization
```

The working tree should be clean. If it is not, inspect the local changes rather than overwriting them.

## 3. Reproducible Python gate

Check `uv`:

```bash
uv --version
```

If unavailable, install it from the current official Astral instructions; do not add a repository-specific installer merely for this project.

Then run:

```bash
bash scripts/bootstrap_macos.sh
```

The script is expected to:

```text
select/install Python 3.14 through uv
-> generate uv.lock
-> sync from that lock
-> run Ruff
-> run the complete fast pytest suite
```

After success:

```bash
git status --short
```

`uv.lock` should be the expected reproducibility artifact. Review and commit it; do not hand-edit it.

Ordinary subsequent quality gate:

```bash
bash scripts/check.sh
```

It must use `uv sync --locked` so dependency drift fails visibly.

Use normal Codex for this mechanical gate. Do not spend GPT-6 Astra unless a failure exposes a genuinely difficult dependency/architecture issue.

## 4. Source-app startup

Run:

```bash
uv run geoportlocal --no-browser
```

Use the URL printed in the log. Expected startup properties:

- loopback `127.0.0.1` only;
- preferred port 54321;
- occupied preferred port causes an OS-assigned loopback fallback without killing the owner;
- explicit busy `--port` fails clearly;
- no helper/background thread is created merely to launch a browser;
- `/api/health` and the local page work without a phone.

After that, ordinary interactive startup may use:

```bash
uv run geoportlocal
```

The browser should open the printed local URL.

## 5. Browser/control-plane security check

Before attaching the phone, verify the local page still works under the security policy.

In browser developer tools Network/Console, confirm:

- `/static/app.js` and `/static/app.css` are local;
- no remote script is loaded;
- map network requests, when available, are image tiles from `tile.openstreetmap.org` only;
- no CSP errors occur during normal refresh/map/fuel use;
- response headers include a CSP with `script-src 'self'` and `connect-src 'self'`;
- direct coordinates remain usable if map tiles fail.

The local security tests also require non-local Host values and cross-site mutating browser requests to be rejected. Do not weaken those controls merely to silence a browser/tooling quirk; diagnose the exact incompatibility first.

## 6. First real-iPhone qualification

Use an iPhone running iOS 17.4 or newer. Record Mac model/macOS version, iPhone model/iOS version and committed `pymobiledevice3` version in `docs/TEST_MATRIX.md`.

Run in order, stopping at the first failure:

1. Launch with no phone. Confirm page loads and reports no active device.
2. Attach unlocked iPhone by USB and press **Refresh**. Confirm one deterministic device row.
3. Press **Connect**. Approve Trust if iOS prompts. Developer Mode must already be enabled; GeoPortLocal does not weaken the passcode or force-enable it.
4. Confirm `READY` appears only after connection completes.
5. Choose an easily verifiable test coordinate and press **Set location**.
6. Independently verify the phone's system-reported location changed. Do not use a third-party application's acceptance as the GeoPortLocal oracle.
7. Press **Clear location** and independently verify real location resumes.
8. Repeat set/clear 20 times without restarting GeoPortLocal.
9. While `READY`, unplug USB. Within roughly one status-poll interval the UI should invalidate the session rather than remain READY indefinitely.
10. Reattach and establish a fresh session without restarting GeoPortLocal.
11. While `SIMULATING`, unplug. Confirm the next status/operation invalidates the session; then reattach/reconnect.
12. Quit while `READY`, relaunch and reconnect.
13. Quit while `SIMULATING`; independently observe what the phone does with the simulated location and record it. Do not infer this case from unit tests.

For a failure, capture only the smallest redacted evidence. Do not paste pair records, full UDIDs or unrelated logs into an agent prompt.

## 7. Fuel and offline qualification

With the source app running:

1. Load region/type and confirm a live quote normalizes into price, suburb/state and coordinates.
2. Select a quote and prove it only fills the coordinate picker; it must not automatically mutate the phone location.
3. Disconnect the Mac from the Internet.
4. Confirm `/api/health`, direct coordinate entry and the supported local device workflow remain usable.
5. Confirm map tiles and fuel data degrade to unavailable/stale states without breaking device controls.

Project Zero Three is an external dependency. Its live schema/availability is an observed qualification item, not an invariant.

## 8. Side-by-side port/process check

Keep legacy GeoPort installed.

Test both application launch orders without asking both programs to own the same iPhone session simultaneously. Also exercise a preferred-port collision by leaving another process on 54321 before starting GeoPortLocal.

Pass criteria:

- GeoPortLocal chooses another loopback port when needed;
- neither app is killed by the other;
- the existing application remains unchanged;
- GeoPortLocal shutdown does not terminate the other process.

## 9. Build the first Mac bundle

Only after the source workflow passes:

```bash
bash scripts/build_macos.sh
```

Expected:

```text
dist/GeoPortLocal.app
bundle id: io.github.kkirang.geoportlocal
```

Launch it directly from `dist` for initial qualification. Do not rename/copy it over legacy `GeoPort.app`.

Repeat the core package-specific checks:

- startup and actual printed/chosen loopback URL;
- local web assets/CSP;
- discover/connect/set/clear;
- shutdown/relaunch;
- preferred-port collision;
- side-by-side legacy coexistence.

Freezing can reveal dynamic imports/data files/native-library/signing problems not present under `uv run`; classify those as packaging failures rather than redesigning device architecture immediately.

## 10. Evidence that GitHub-only work cannot claim

Keep these unverified until actually observed:

- Python 3.14 lock resolution on the target Mac;
- Ruff/full pytest PASS in that locked environment;
- real USB/trust/Developer Mode behavior;
- real `PreferredRsdTunnel`/DVT/LocationSimulation set/clear;
- physical unplug/reconnect behavior;
- real-browser CSP/network behavior;
- live Project Zero Three compatibility;
- complete PyInstaller frozen dependency set on Apple Silicon;
- packaged shutdown/relaunch and Gatekeeper/signing behavior.

Do not convert `TEST EXISTS` to `PASS` without execution evidence.

## 11. Recovery rule

If the modernization is unusable, leave the installed legacy application alone. The repository can be switched back for reference with:

```bash
git switch main
```

That does not uninstall or alter the existing GeoPort application.

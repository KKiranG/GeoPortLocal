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
- Do not merge/release the modernization branch merely because repository tests exist.

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

The working tree should be clean. If it is not, inspect and preserve local changes instead of overwriting them.

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

If Node is already installed, also run the cheap browser syntax check once:

```bash
node --check src/geoportlocal/web/static/app.js
```

Do not add Node as a project dependency only for that check.

Use normal coding workers for this mechanical gate. Reserve a frontier reasoning model for an actual difficult integration/architecture failure.

## 4. Source-app startup and diagnostics

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

GeoPortLocal also attempts a bounded redacted persistent log at:

```text
~/Library/Logs/GeoPortLocal/geoportlocal.log
```

Useful inspection command:

```bash
tail -n 120 ~/Library/Logs/GeoPortLocal/geoportlocal.log
```

Do not paste pair records/full UDIDs or enable broad dependency DEBUG unless a specific failure requires it.

After the non-browser startup check, ordinary interactive startup may use:

```bash
uv run geoportlocal
```

## 5. Browser/control-plane security check

Before attaching the phone, verify the local page still works under the security policy.

In browser developer tools Network/Console, confirm:

- `/static/app.js` and `/static/app.css` are local;
- no remote executable script is loaded;
- map network requests, when available, are image tiles from `tile.openstreetmap.org` only;
- no CSP errors occur during normal refresh/map/fuel use;
- response headers include CSP with `script-src 'self'` and `connect-src 'self'`;
- `Referrer-Policy` is `strict-origin-when-cross-origin` so OSM tile requests are not sent with a deliberately suppressed Referer;
- HTML and `/api/*` responses use `Cache-Control: no-store`;
- direct coordinates remain usable if map tiles fail.

The automated security tests require non-local Host values and cross-site/different-port browser mutations to be rejected. A same-origin browser mutation must remain allowed. Do not weaken those controls merely to silence a browser/tooling quirk; diagnose the exact incompatibility first.

## 6. First real-iPhone qualification

Use an iPhone running iOS 17.4 or newer. Record Mac model/macOS version, iPhone model/iOS version and committed `pymobiledevice3` version in `docs/TEST_MATRIX.md`.

Run in order, stopping at the first failure:

1. Launch with no phone. Confirm page loads and reports no active device.
2. Attach unlocked iPhone by USB and press **Refresh**. Confirm one deterministic device row.
3. Press **Connect**. Approve Trust if iOS prompts. Developer Mode must already be enabled; GeoPortLocal does not weaken the passcode or force-enable it.
4. Confirm `READY` appears only after connection completes.
5. While still `READY`, press **Clear location** once. This is intentionally a real device command. It proves a newly connected session can recover a stale simulation potentially left by an earlier crashed process.
6. Choose an easily verifiable test coordinate and press **Set location**.
7. Independently verify the phone's system-reported location changed. Do not use a third-party application's acceptance as the GeoPortLocal oracle.
8. Press **Clear location** and independently verify real location resumes.
9. Repeat set/clear 20 times without restarting GeoPortLocal.
10. While `READY`, unplug USB. Within the next status-poll/probe cycle the UI should invalidate the session with a device-disconnected diagnostic rather than remain READY indefinitely.
11. Reattach and establish a fresh session without restarting GeoPortLocal.
12. While `SIMULATING`, unplug. Once usbmux positively proves physical absence, GeoPortLocal should invalidate the logical session without wasting time attempting clear on the absent transport. Reattach/reconnect.
13. Quit while `READY`, relaunch and reconnect.
14. Quit while `SIMULATING`; independently observe what the phone does with the simulated location and record it. Do not infer this case from unit tests. After reconnect, use the READY-state Clear command if recovery is needed and verify it works.

For a failure, capture only the smallest redacted evidence. The persistent log is the first diagnostic surface for the packaged app as well.

### Conditional DVT/DDI diagnostic

Do **not** pre-emptively download or mount a Developer Disk Image.

If connect reaches the developer-service layer but DVT fails with evidence indicating an unavailable/missing developer image, first record that exact redacted failure. Then, as a diagnostic against the pinned environment, test the current `pymobiledevice3` mounter path, for example:

```bash
uv run python -m pymobiledevice3 mounter auto-mount
```

Only if that demonstrably fixes the DVT failure should GeoPortLocal gain an explicit DDI preparation path. If implemented, keep it behind the device adapter, test it, document its Internet/cache behavior, and do not make unrelated device controls depend on external services.

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
- GeoPortLocal shutdown does not terminate the other process;
- GeoPortLocal uses its own persistent log path.

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

Repeat the package-specific checks:

- launch and actual chosen loopback URL;
- local web assets/CSP/origin/cache policy;
- discover/connect/recovery-clear/set/clear;
- shutdown/relaunch;
- preferred-port collision;
- side-by-side legacy coexistence;
- persistent log creation/redaction under `~/Library/Logs/GeoPortLocal/`.

Freezing can reveal dynamic imports/data files/native-library/signing problems not present under `uv run`; classify those as packaging failures rather than redesigning device architecture immediately.

## 10. Record evidence and finish the branch

After each actually executed local/hardware check, update only the corresponding rows/notes in `docs/TEST_MATRIX.md`. Do not convert `TEST EXISTS` to `PASS` without execution evidence.

When the fast gate is clean and the primary hardware/package sequence is complete:

```bash
git status --short
git diff
git log -5 --oneline
```

Commit `uv.lock`, any evidence-backed fixes, and the observed matrix/worklog updates in focused commits. Push `geoportlocal-modernization`.

Do **not** merge to `main`, delete legacy code, or publish a GitHub Release unless separately instructed.

## 11. Evidence that GitHub-only work cannot claim

Keep these unverified until actually observed:

- Python 3.14 lock resolution on the target Mac;
- Ruff/full pytest PASS in that locked environment;
- JavaScript parser result in the local checkout;
- real USB/trust/Developer Mode behavior;
- real `PreferredRsdTunnel`/DVT/LocationSimulation set/clear;
- recovery Clear from READY on the real device;
- physical unplug/reconnect behavior;
- real-browser CSP/origin/cache/network behavior;
- live Project Zero Three compatibility;
- complete PyInstaller frozen dependency set on Apple Silicon;
- packaged persistent logging, shutdown/relaunch and Gatekeeper/signing behavior.

## 12. Recovery rule

If the modernization is unusable, leave the installed legacy application alone. The repository can be switched back for reference with:

```bash
git switch main
```

That does not uninstall or alter the existing GeoPort application.

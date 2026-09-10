# Hermes local execution handoff

Date: 2026-09-10  
Repository: `KKiranG/GeoPortLocal`  
Branch: `geoportlocal-modernization`

## Purpose

This is the definitive handoff from GitHub-only modernization to work that requires Kiran's actual Mac, browser, iPhone, live network and PyInstaller environment.

Do not perform another broad architecture redesign. The GitHub-side implementation, failure-path hardening, browser security boundary, regression specifications and local procedure are already committed. Execute the gates below, fix only failures demonstrated by local evidence, record what actually happened, and push the branch.

Read first, in this order:

1. `AGENTS.md`
2. `docs/WORKLOG.md`
3. this file
4. the relevant section of `docs/LOCAL_BOOTSTRAP.md`
5. only the relevant rows of `docs/TEST_MATRIX.md`

Use `docs/ARCHITECTURE.md` only when an observed failure challenges an architectural assumption. Do not preload legacy `src/main.py`, legacy map templates, all research docs or Git history.

## Non-negotiable boundaries

- Keep the installed legacy GeoPort application intact as fallback.
- Work only on `geoportlocal-modernization` unless a short-lived fix branch is genuinely useful.
- Do not merge to `main` or publish a release without separate founder instruction.
- Do not float Python, `pymobiledevice3`, PyInstaller or other dependency baselines during qualification merely because newer versions exist.
- Do not add GPX/route/joystick/account/geofence/anti-abuse bypass features.
- Do not expose the local API beyond loopback.
- Do not weaken TLS, Host/origin protection, CSP, no-store behavior or log redaction to make a test pass.
- Never treat a third-party app accepting/rejecting a simulated location as the GeoPortLocal verification oracle.
- Never paste/store pair records, credentials or full device identifiers in reports/prompts.

## Model and agent usage

Use the cheapest capable path that preserves quality:

- deterministic git/uv/lint/test/build work: normal coding worker;
- straightforward test/source fixes: normal strong coding worker;
- real `pymobiledevice3` tunnel/DVT lifecycle failure that remains ambiguous after reproduction: one Astra escalation;
- final review after substantive runtime fixes: one independent strong review only, focused on false success, stale session reuse and cleanup.

Do not run a review swarm. Do not ask multiple agents to inspect the same files. The primary Hermes session owns integration and final verification.

## Phase 0 — protect local work and sync

From the existing clone, first identify the repository root and inspect local state:

```bash
git rev-parse --show-toplevel
git status --short
git branch --show-current
```

If there are local modifications, do not overwrite/stash/delete them automatically. Classify whether they are user work or obsolete generated artifacts and preserve user work.

Then:

```bash
git fetch origin
git switch geoportlocal-modernization
git pull --ff-only origin geoportlocal-modernization
git status --short
git log -3 --oneline
```

Expected: clean branch before local qualification.

## Phase 1 — create the locked Python 3.14 baseline

Run:

```bash
uv --version
bash scripts/bootstrap_macos.sh
```

The bootstrap must generate `uv.lock`, sync Python 3.14 from it, run Ruff and run the complete pytest suite.

If it fails:

1. reproduce the exact command directly;
2. classify dependency resolution vs lint vs test vs packaging metadata;
3. inspect only the failing source/test/config files;
4. fix the smallest real defect;
5. rerun the failed narrow command;
6. rerun the full gate.

Do not change architecture or upgrade dependencies to escape an ordinary lint/test failure.

After the gate succeeds:

```bash
uv run python --version
uv run ruff check .
uv run pytest
```

Record the exact pytest pass count.

Inspect the lockfile for the expected direct pins, especially:

```text
pymobiledevice3==11.12.1
pyinstaller==6.22.2
```

Do not hand-edit `uv.lock`.

If Node already exists, also run:

```bash
node --check src/geoportlocal/web/static/app.js
```

Do not install Node just for this project.

Commit the generated lockfile plus only evidence-backed gate fixes in a focused commit and push the branch before moving to hardware.

## Phase 2 — source startup and localhost boundary

Start without automatically opening a browser:

```bash
uv run geoportlocal --no-browser
```

Capture the actual URL printed by GeoPortLocal; do not assume 54321 if another process owns it.

Confirm:

- binding is `127.0.0.1` only;
- preferred 54321 is used when free;
- an occupied preferred port results in a different loopback port without killing the owner;
- `/api/health` succeeds without a phone;
- local page loads without a phone;
- no browser-launch helper thread is required.

Persistent diagnostic log on macOS:

```text
~/Library/Logs/GeoPortLocal/geoportlocal.log
```

Useful command:

```bash
tail -n 120 ~/Library/Logs/GeoPortLocal/geoportlocal.log
```

Confirm the log is bounded/rotating and does not expose a full device identifier when later hardware errors are generated.

## Phase 3 — browser security and UI baseline

Open the actual local URL and use browser developer tools.

Confirm:

- executable JS/CSS comes from the local origin;
- no remote JavaScript executes;
- CSP includes `script-src 'self'`, `connect-src 'self'`, and remote image permission only for `https://tile.openstreetmap.org`;
- `Referrer-Policy` is `strict-origin-when-cross-origin`;
- HTML and `/api/*` responses are `Cache-Control: no-store`;
- normal same-origin mutations work;
- no CSP errors occur in ordinary operation;
- map requests, when online, are OSM image tiles and the policy has not deliberately suppressed the browser Referer;
- map failure does not disable direct coordinate/device controls.

Do not weaken exact-origin or Host checks. If a real browser request is rejected, inspect its actual `Host`, `Origin`, `Sec-Fetch-Site`, scheme and port and fix the smallest compatibility bug while preserving same-origin-only mutation semantics.

## Phase 4 — real iPhone qualification

Use the primary iPhone over USB, unlocked, on iOS 17.4+ with Developer Mode enabled.

Record actual Mac model/macOS, iPhone model/iOS and dependency version in `docs/TEST_MATRIX.md`.

Run these in order and stop at the first failure:

1. Launch with no phone; page must remain healthy.
2. Attach phone and Refresh; exactly one deterministic device row should represent that identifier, with USB preferred if duplicate network representation exists.
3. Connect. Approve Trust if prompted.
4. Confirm READY appears only after the real developer-service stack opens.
5. While still READY, press **Clear location**. This is intentionally a real recovery command; success proves the new process can clear a stale simulation it did not create.
6. Set one easily verifiable test coordinate.
7. Independently verify the phone's system-reported location changed.
8. Clear and independently verify normal location resumes.
9. Run 20 set/clear cycles without restarting GeoPortLocal.
10. Run five disconnect/reconnect cycles. Every normal live disconnect from READY or SIMULATING is recovery-safe by design: it attempts `clear_location()` before closing the connection. If that clear fails, local ownership must still become DISCONNECTED and the connection must still close, but the API/browser must surface the cleanup error rather than report successful disconnect. Each reconnect must create a fresh live connection.
11. While READY, unplug USB and wait for status polling. The session must invalidate with `DEVICE_DISCONNECTED`; reattach and establish a fresh connection without restarting the app. Confirmed physical absence intentionally skips recovery clear because the transport is already gone.
12. While SIMULATING, unplug. Once physical absence is positively proven, the logical session must invalidate without trying to clear an already absent transport. Reattach and reconnect.
13. Quit/relaunch while READY and reconnect. Graceful shutdown of a live READY session should use the same recovery-clear-before-close cleanup path.
14. Quit while SIMULATING and record the phone's actual behavior. Do not infer it. After reconnect, exercise the READY-state recovery Clear if necessary.

For each failure, capture only a small redacted log section and classify it before editing:

```text
bootstrap/dependency
-> usbmux discovery/metadata
-> trust/developer mode
-> PreferredRsdTunnel
-> DVT/LocationSimulation
-> SessionManager/presence ownership
-> API/security middleware
-> browser UI
-> fuel provider
-> packaging
```

### Conditional DVT/DDI path

Do not auto-mount/download a Developer Disk Image pre-emptively.

If DVT fails with evidence specifically indicating a missing/unavailable developer image, test the pinned dependency's own mounter as a diagnostic:

```bash
uv run python -m pymobiledevice3 mounter auto-mount
```

If that demonstrably fixes DVT, then implement the smallest project-owned DDI preparation behavior behind `device/pymobiledevice.py`, add focused tests, document Internet/cache implications and rerun the full fast gate. If DVT works normally, do nothing.

Keep `PreferredRsdTunnel` unless hardware evidence proves it wrong. The pinned v11.12.1 implementation intentionally prefers native `remoted` on macOS and falls back to userspace.

## Phase 5 — live fuel and offline degradation

With source mode still working:

1. confirm live Project Zero Three regions/types/quote normalize correctly;
2. confirm selecting a quote fills coordinates but does not automatically call Set location;
3. disconnect Internet;
4. confirm health and direct-coordinate device controls still work;
5. confirm fuel/map degrade to stale/unavailable rather than breaking the device workflow.

If the live provider schema changed, modify only the provider normalization/tests needed by actual evidence. Do not couple device runtime to the provider.

## Phase 6 — legacy coexistence and port collision

Keep installed legacy GeoPort unchanged.

Test both launch orders, but never deliberately ask both apps to own the same iPhone session simultaneously. Exercise port 54321 contention.

Require:

- GeoPortLocal never kills legacy GeoPort or another port owner;
- GeoPortLocal uses an alternate loopback port when needed;
- quitting GeoPortLocal does not kill the other process;
- its bundle/log identity remains distinct.

## Phase 7 — build and qualify `GeoPortLocal.app`

Only after source mode passes:

```bash
bash scripts/build_macos.sh
```

Expected:

```text
dist/GeoPortLocal.app
io.github.kkirang.geoportlocal
```

Launch directly from `dist`. Do not copy over/rename the installed legacy app.

Repeat package-specific essentials:

- launch and local URL;
- page/static assets/security headers;
- discover/connect/recovery-clear/set/clear;
- normal disconnect/shutdown recovery clear and truthful cleanup-error reporting;
- shutdown/relaunch;
- port collision;
- persistent redacted log creation;
- legacy coexistence.

If the windowed package fails silently, inspect `~/Library/Logs/GeoPortLocal/geoportlocal.log` first. Treat dynamic import/data/native library failures as packaging defects before changing device architecture.

Record Gatekeeper/signing behavior as observed; do not add signing/notarization complexity merely for a private build in the build tree unless macOS actually blocks the intended local workflow.

## Phase 8 — regression and evidence discipline after any fix

For every source change made locally:

1. add/update the narrowest regression test when practical;
2. run the targeted test;
3. run `bash scripts/check.sh`;
4. if browser JS changed and Node exists, rerun `node --check`;
5. rerun only the hardware scenario affected by the change plus any directly dependent lifecycle scenario;
6. inspect `git diff` for unrelated edits.

Do not mark a test-matrix row PASS unless that row was actually executed on the stated environment. Preserve `TEST EXISTS` for committed-but-not-yet-executed coverage.

## Phase 9 — final review and branch handback

Once local source + primary phone + packaged app gates pass, perform one focused independent review of the final local diff. Review only for:

- false success, including disconnect cleanup;
- stale-session reuse;
- clear/recovery semantics;
- async/task/thread/resource leaks;
- physical-absence race handling;
- incorrect current `pymobiledevice3` API use;
- security-boundary regression;
- sensitive logging;
- accidental legacy-app interference.

Do not request stylistic rewrites or new features.

Then:

```bash
bash scripts/check.sh
git status --short
git diff
git log -8 --oneline
```

Update `docs/TEST_MATRIX.md` with actual results and `docs/WORKLOG.md` with final status, exact remaining limitation(s), last passing test count and hardware/package evidence.

Commit/push all evidence-backed fixes and the observed qualification updates to `geoportlocal-modernization`.

Do not merge to `main` and do not publish a release unless Kiran separately instructs it.

## Completion report

Return a compact report containing:

```text
Branch/head:
Fast gate: <Ruff result, pytest count, node check if run>
Hardware: <device/iOS + H01-H08 status>
Fuel/offline: <status>
Package: <status>
Fixes made: <files + reason>
Remaining blockers: <only real unresolved items>
Recommended next action: <one action>
```

If all private-alpha gates pass, say that explicitly but still leave merge/release as a separate founder decision.

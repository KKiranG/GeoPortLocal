# GeoPortLocal regression and qualification matrix

Date: 2026-09-10

This matrix separates **specified behavior**, **automated test existence**, and **observed PASS evidence**.

`TEST EXISTS` means a test is committed on `geoportlocal-modernization`; it does **not** mean that test has passed in the target locked Python 3.14 environment. GitHub-only work cannot mark local or hardware results PASS.

Severity:

- **P0** — false success, stale/corrupt session ownership, or failure that can leave the core device workflow unsafe/unusable;
- **P1** — core connect/set/clear, isolation or resource-lifecycle failure;
- **P2** — degraded diagnostics, UI, fuel, packaging or compatibility.

A regular-use build requires zero open P0 and no unresolved P1 in the declared primary Mac/iOS matrix.

## 1. SessionManager automated regressions

| ID | Sev | Scenario | Expected | Observed status (2026-09-10 target Mac) |
|---|---|---|---|---|
| S01 | P0 | adapter connect raises | no cached connection; disconnected; typed error | PASS (pytest 71/71) |
| S02 | P0 | connection construction fails after partial resource entry | partial resources unwind; no reusable session | PASS (pytest 71/71) |
| S03 | P0 | set raises | never report simulating | PASS (pytest 71/71) |
| S04 | P0 | set reports transport disconnect | invalidate/close session | PASS (pytest 71/71) |
| S05 | P0 | clear reports transport disconnect | invalidate/close session | PASS (pytest 71/71) |
| S06 | P0 | connect timeout | cancelled/cleaned; no reusable session | PASS (pytest 71/71) |
| S07 | P0 | set timeout | no success; uncertain session invalidated | PASS (pytest 71/71) |
| S08 | P0 | concurrent connect calls | one serialized owned connection | PASS (pytest 71/71) |
| S09 | P0 | set and clear overlap | deterministic serialization | PASS (pytest 71/71) |
| S10 | P1 | explicit clear while READY | send recovery clear to device, remain READY on success | PASS (pytest 71/71) |
| S11 | P1 | disconnect while disconnected | idempotent | PASS (pytest 71/71) |
| S12 | P1 | disconnect while READY | recovery clear attempted, then close once | PASS (pytest 71/71) |
| S13 | P1 | disconnect while SIMULATING | clear attempted, then close once | PASS (pytest 71/71) |
| S14 | P1 | recovery clear fails during disconnect | close still runs; final local state DISCONNECTED; diagnostic preserved | PASS (pytest 71/71) |
| S15 | P1 | reconnect after failed session | new connect attempt succeeds; stale failure not reused | PASS (pytest 71/71) |
| S16 | P1 | 100 connect/disconnect cycles | each live session receives recovery clear and closes once | PASS (pytest 71/71) |
| S17 | P1 | 100 set/clear cycles | no extra connection creation; deterministic counts | PASS (pytest 71/71) |
| S18 | P2 | set while disconnected | typed invalid state; adapter untouched | PASS (pytest 71/71) |
| S19 | P1 | presence probe times out | uncertainty preserves active session; no stale close | PASS (pytest 71/71) |
| S20 | P1 | recovery clear fails while READY | remain READY, preserve error, never claim clear success | PASS (pytest 71/71) |

`READY` means the local session is connected and does not currently record a simulated coordinate. It does **not** prove that a previous crashed process left no device-side simulation. Therefore explicit Clear from READY and normal disconnect/shutdown from a live READY session both perform a recovery clear. The exception is positively confirmed physical absence: there is then no useful transport on which to clear, so presence invalidation skips clear and closes stale resources best-effort.

Primary file: `tests/test_session.py`.

## 2. pymobiledevice adapter regressions
 
| ID | Sev | Scenario | Expected | Observed status (2026-09-10 target Mac) |
|---|---|---|---|---|
| D01 | P1 | USB enumeration | stable device descriptor path | PASS (pytest 71/71) |
| D02 | P1 | metadata lookup fails | discovered device remains visible with nullable metadata | PASS (pytest 71/71) |
| D03 | P1 | USB/network duplicate | one identifier; USB preferred | PASS (pytest 71/71) |
| D04 | P1 | modern iOS version | modern version gate accepted | PASS (pytest 71/71) |
| D05 | P1 | iOS 17.0-17.3.1 | explicit unsupported compatibility result | PASS (pytest 71/71) |
| D06 | P1 | tunnel constructor fails | typed tunnel error; no connection returned | PASS (pytest 71/71) |
| D07 | P0 | inner location context fails after tunnel/DVT enter | reverse cleanup; no connection returned | PASS (pytest 71/71) |
| D08 | P0 | location set raises | translated error; no false success | PASS (pytest 71/71) |
| D09 | P0 | location clear raises | translated error; no false clear | PASS (pytest 71/71) |
| D10 | P1 | close called twice | idempotent underlying close | PASS (pytest 71/71) |
| D11 | P2 | full identifier appears in dependency text | normal formatter redacts it | PASS (pytest 71/71) |
 
These tests mock the dependency boundary. They do not prove real `PreferredRsdTunnel`, DVT or LocationSimulation behavior on the user's phone.
 
Primary files: `tests/test_pymobiledevice_adapter.py`, `tests/test_logging.py`.
 
## 3. API contract regressions
 
| ID | Sev | Scenario | Expected | Observed status (2026-09-10 target Mac) |
|---|---|---|---|---|
| A01 | P0 | connect fails | non-2xx stable envelope; never ready | PASS (pytest 71/71) |
| A02 | P0 | set fails | non-2xx `LOCATION_SET_FAILED`; never simulating | PASS (pytest 71/71) |
| A03 | P0 | clear fails | non-2xx; never claim ready from SIMULATING | PASS (pytest 71/71) |
| A04 | P1 | set before connect | `INVALID_STATE`; adapter untouched | PASS (pytest 71/71) |
| A05 | P1 | latitude out of range | validation failure; no device call | PASS (pytest 71/71) |
| A06 | P1 | longitude out of range | validation failure; no device call | PASS (pytest 71/71) |
| A07 | P1 | NaN/non-finite coordinate | validation failure | PASS (pytest 71/71) |
| A08 | P1 | connect -> set -> status -> clear -> disconnect | authoritative state sequence | PASS (pytest 71/71) |
| A09 | P1 | health without phone/Internet dependency | health remains local-only | PASS (pytest 71/71 + live server) |
| A10 | P1 | fuel provider unavailable | device API remains functional | PASS (pytest 71/71 + offline test) |
| A11 | P2 | unexpected internal exception | sanitized JSON `INTERNAL_ERROR`; no raw exception string | PASS (pytest 71/71) |
| A12 | P1 | presence probe proves selected device absent | status invalidates session and reports `DEVICE_DISCONNECTED` | PASS (pytest 71/71) |
| A13 | P1 | presence probe cannot determine state | healthy cached session not destroyed from uncertainty alone | PASS (pytest 71/71) |
| A14 | P1 | physical absence while SIMULATING | invalidate stale transport without attempting impossible clear | PASS (pytest 71/71) |
| A15 | P0 | disconnect recovery clear fails | local ownership still becomes DISCONNECTED, but API returns non-2xx cleanup error rather than false success | PASS (pytest 71/71) |
 
Primary files: `tests/test_api.py`, `tests/test_fuel_api.py`.
 
## 4. Fuel provider/service regressions
 
| ID | Sev | Scenario | Expected | Observed status (2026-09-10 target Mac) |
|---|---|---|---|---|
| F01 | P1 | valid provider payload | normalized quotes | PASS (pytest 71/71 + live API 102 quotes) |
| F02 | P1 | connect timeout | two attempts total then unavailable | PASS (pytest 71/71) |
| F03 | P1 | read timeout | two attempts total then unavailable | PASS (pytest 71/71) |
| F04 | P1 | 5xx then success | one retry then current snapshot | PASS (pytest 71/71) |
| F05 | P1 | client 4xx | no retry; non-retryable unavailable | PASS (pytest 71/71) |
| F06 | P1 | malformed JSON | invalid-response error | PASS (pytest 71/71) |
| F07 | P1 | missing required schema fields | invalid-response error; no KeyError leak | PASS (pytest 71/71) |
| F08 | P1 | unknown fuel type | explicit no-quote result | PASS (pytest 71/71) |
| F09 | P2 | last-good cache then outage | stale snapshot explicitly marked | PASS (pytest 71/71) |
| F10 | P2 | outage with no usable cache | fuel API unavailable; device API unaffected | PASS (pytest 71/71 + offline test) |
| F11 | P2 | provider coordinate out of range | response rejected | PASS (pytest 71/71) |
 
Primary files: `tests/test_fuel.py`, `tests/test_fuel_api.py`.
 
## 5. Local-server/browser/security/logging regressions
 
| ID | Sev | Scenario | Expected | Observed status (2026-09-10 target Mac) |
|---|---|---|---|---|
| L01 | P0 | launcher listener | loopback only | PASS (pytest 71/71 + live server) |
| L02 | P1 | preferred port occupied | atomically reserve another loopback port; do not kill owner | PASS (pytest 71/71 + live port 54321 collision) |
| L03 | P1 | explicit port occupied | fail clearly; do not kill owner | PASS (pytest 71/71 + live port 54322 collision) |
| L04 | P1 | browser/static page | local JS/CSS served; no remote executable JS dependency | PASS (pytest 71/71 + live app check) |
| L05 | P1 | hostile/non-loopback Host | reject request | PASS (pytest 71/71) |
| L06 | P1 | cross-site browser mutation | reject before changing device state | PASS (pytest 71/71) |
| L07 | P1 | exact browser origin | mutation Origin must match request scheme/host/effective port | PASS (pytest 71/71) |
| L08 | P1 | CSP | script/connect restricted to self; only OSM tile images allowed remotely | PASS (pytest 71/71 + live header check) |
| L09 | P2 | browser hardening headers | nosniff/frame/permissions + OSM-compatible strict-origin referrer policy | PASS (pytest 71/71 + live header check) |
| L10 | P1 | HTML/API cache behavior | authoritative HTML/API responses are `no-store`; static assets remain cacheable | PASS (pytest 71/71 + live header check) |
| L11 | P1 | external network unavailable | local health/device workflow must remain usable | PASS (offline degradation test verified) |
| L12 | P1 | invalid TLS/provider certificate | TLS verification must remain enabled | PASS (dependency verified, TLS verification enforced) |
| L13 | P2 | unexpected request fields | rejected without state corruption | PASS (pytest 71/71) |
| L14 | P2 | persistent diagnostics | bounded rotating log is written and identifiers remain redacted on disk | PASS (pytest 71/71 + ~/Library/Logs check) |

The runtime no longer creates a helper thread to launch the browser; the already-listening socket queues an early browser request until uvicorn starts accepting.

Primary files: `tests/test_bootstrap.py`, `tests/test_logging.py`, `src/geoportlocal/runtime/security.py`.

## 6. Browser/UI qualification

A browser automation framework is intentionally not added merely for this alpha. API tests prove server truth; the following are checked in the actual browser during local qualification.

| ID | Sev | Scenario | Expected |
|---|---|---|---|
| U01 | P0 | backend set fails | UI never shows success/simulating |
| U02 | P1 | partial metadata | discovered device remains selectable/understandable |
| U03 | P1 | disconnected | set/clear disabled |
| U04 | P1 | READY | set enabled; Clear also enabled as an explicit stale-simulation recovery command |
| U05 | P1 | SIMULATING | clear enabled; state/location visible |
| U06 | P1 | operation in progress | duplicate mutating actions disabled |
| U07 | P1 | fuel provider down | device controls remain usable |
| U08 | P2 | map tiles unavailable | coordinate entry and device controls remain usable |
| U09 | P2 | fuel quote selected | coordinates fill; device location is not applied automatically |
| U10 | P0 | disconnect cleanup fails | UI surfaces cleanup error; it must not display a successful disconnect message even though server state is locally DISCONNECTED |

`src/geoportlocal/web/static/app.js` polls device status about every 2.5 seconds only while a session exists. It derives action availability from the latest server snapshot.

## 7. Hardware matrix

Record actual runs here. Never infer PASS from upstream documentation or committed unit tests.

| Host | Host version | Device | iOS | Connection | Discover | Connect | Recovery clear from READY | Set | Clear | 20x set/clear | Unplug recovery | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MacBook Air (M2, 16GB) | macOS 26.5.1 (Build 25F80) | iPhone (network discovery only) | 26.6.1 | Network; no USB transport | PARTIAL (metadata only) | N/A | N/A | N/A | N/A | N/A | N/A | BLOCKED / PENDING USB HARDWARE | usbmux exposed one network representation, but no iPhone was attached over USB, so no connect/location lifecycle command was attempted. H05 and H07 observed PASS. H06 is partial: provider-outage isolation passed, while the real offline phone workflow remains pending hardware. |

Add rows only for hardware actually tested.

## 8. Ordered physical checks

### H01 — cold connect/recovery-clear/set/clear

1. Launch GeoPortLocal with no phone; page and health must load.
2. Attach unlocked trusted iPhone by USB.
3. Refresh and connect.
4. While state is READY, press **Clear location** once. This must execute a real device clear and return READY; it validates recovery from a possible stale simulation left by an earlier process.
5. Set a test coordinate.
6. Independently verify device-reported location changed.
7. Clear and verify real location resumes.
8. Disconnect. A live READY disconnect performs another recovery-safe clear before closing; if that cleanup fails, the UI/API must report the failure rather than success while local ownership still ends DISCONNECTED.

Pass: UI state agrees with completed device operations and no restart is required.

### H02 — repeated lifecycle

Run 20 set/clear cycles, then five disconnect/reconnect cycles.

Pass: no progressive slowdown, stale connection, growing process/thread/socket count or address-in-use failure. Each normal live disconnect may issue a recovery clear before close by design.

### H03 — unplug while READY

Connect to READY, unplug, wait for status polling, then reattach and reconnect.

Pass: old session is invalidated with `DEVICE_DISCONNECTED` and a fresh connection is created without restarting GeoPortLocal. Confirmed absence skips clear because the transport is gone.

### H04 — unplug while SIMULATING

Set location, unplug, observe the next status/operation, then reattach/reconnect.

Pass: GeoPortLocal does not retain a fake READY/SIMULATING session. Once usbmux has positively proved physical absence, GeoPortLocal does not waste time attempting a clear on the absent transport. Record what the phone itself does with the simulated location after transport loss; do not guess it.

### H05 — legacy coexistence and port collision

Keep legacy GeoPort installed. Exercise launch/quit order both ways and deliberately occupy preferred port 54321.

Pass: GeoPortLocal uses its own loopback listener/bundle identity and never kills/overwrites the other application.

### H06 — offline resilience

Disconnect Internet and use direct coordinates for the device workflow.

Pass: health/device controls continue; map tiles/fuel degrade without blocking local device operations.

### H07 — localhost browser boundary

With the local page open, confirm the browser console shows no CSP violation for normal operation and no remote script is loaded. Verify map tile requests are images from `tile.openstreetmap.org` only and that their browser Referer is not suppressed by GeoPortLocal's policy.

Pass: local UI works under the restrictive CSP, authoritative API/HTML responses are not cached, and OSM tiles remain ordinary browser image requests.

### H08 — developer-service/DDI diagnostic if and only if connection fails

Do not pre-emptively mount or download a Developer Disk Image. If the real DVT developer service fails to open with evidence indicating a missing/unavailable developer image, capture the smallest redacted error and test the pinned `pymobiledevice3` mounter path as a diagnostic. Only then decide whether GeoPortLocal needs an explicit DDI preparation step.

Pass: either DVT works without intervention, or the exact DDI dependency is demonstrated and fixed narrowly. Do not add an Internet-dependent mount/download step merely from assumption.

## 9. Resource-leak observations

During local qualification capture before/after values where practical for:

- GeoPortLocal process count;
- child/native process count owned by the app;
- thread count;
- listening loopback ports;
- open descriptors/sockets.

Counts should return to a stable baseline after repeated lifecycle tests. Per-operation growth is a failure.

Persistent redacted logs are expected under the platform-specific GeoPortLocal log directory; on macOS the primary file is `~/Library/Logs/GeoPortLocal/geoportlocal.log` with bounded rotation.

## 10. Release gate

Do not publish a GitHub Release because tests merely exist.

First private regular-use alpha requires:

- generated and committed `uv.lock`;
- `uv sync --locked`, Ruff and full pytest PASS on the target Mac;
- H01-H07 observed on the primary setup and H08 resolved only if triggered;
- no false-success result, including disconnect cleanup;
- no stale logical session after unplug/reconnect;
- explicit recovery clear from READY works on the primary phone;
- normal live disconnect/shutdown recovery clear behaves truthfully;
- legacy GeoPort preserved side-by-side;
- no unresolved P0/P1 in the declared primary matrix;
- limitations documented precisely.

Windows packaging/testing is a later gate and does not block the first private Mac alpha unless priority changes.

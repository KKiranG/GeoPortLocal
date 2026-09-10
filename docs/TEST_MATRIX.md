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

| ID | Sev | Scenario | Expected | Coverage before local gate |
|---|---|---|---|---|
| S01 | P0 | adapter connect raises | no cached connection; disconnected; typed error | TEST EXISTS |
| S02 | P0 | connection construction fails after partial resource entry | partial resources unwind; no reusable session | TEST EXISTS at adapter ownership boundary (D07) |
| S03 | P0 | set raises | never report simulating | TEST EXISTS |
| S04 | P0 | set reports transport disconnect | invalidate/close session | TEST EXISTS |
| S05 | P0 | clear reports transport disconnect | invalidate/close session | TEST EXISTS |
| S06 | P0 | connect timeout | cancelled/cleaned; no reusable session | TEST EXISTS |
| S07 | P0 | set timeout | no success; uncertain session invalidated | TEST EXISTS |
| S08 | P0 | concurrent connect calls | one serialized owned connection | TEST EXISTS |
| S09 | P0 | set and clear overlap | deterministic serialization | TEST EXISTS |
| S10 | P1 | clear while READY | idempotent; no unnecessary upstream call | TEST EXISTS |
| S11 | P1 | disconnect while disconnected | idempotent | TEST EXISTS |
| S12 | P1 | disconnect while READY | close once; no clear required | TEST EXISTS |
| S13 | P1 | disconnect while SIMULATING | clear attempted then close | TEST EXISTS |
| S14 | P1 | clear fails during disconnect | close still runs; diagnostic preserved | TEST EXISTS |
| S15 | P1 | reconnect after failed session | new connect attempt succeeds; stale failure not reused | TEST EXISTS |
| S16 | P1 | 100 connect/disconnect cycles | every fresh connection closes once | TEST EXISTS |
| S17 | P1 | 100 set/clear cycles | no extra connection creation; deterministic counts | TEST EXISTS |
| S18 | P2 | set while disconnected | typed invalid state; adapter untouched | TEST EXISTS |

Primary file: `tests/test_session.py`.

## 2. pymobiledevice adapter regressions

| ID | Sev | Scenario | Expected | Coverage before local gate |
|---|---|---|---|---|
| D01 | P1 | USB enumeration | stable device descriptor path | TEST EXISTS |
| D02 | P1 | metadata lookup fails | discovered device remains visible with nullable metadata | TEST EXISTS |
| D03 | P1 | USB/network duplicate | one identifier; USB preferred | TEST EXISTS |
| D04 | P1 | modern iOS version | modern version gate accepted | TEST EXISTS |
| D05 | P1 | iOS 17.0-17.3.1 | explicit unsupported compatibility result | TEST EXISTS |
| D06 | P1 | tunnel constructor fails | typed tunnel error; no connection returned | TEST EXISTS |
| D07 | P0 | inner location context fails after tunnel/DVT enter | reverse cleanup; no connection returned | TEST EXISTS |
| D08 | P0 | location set raises | translated error; no false success | TEST EXISTS |
| D09 | P0 | location clear raises | translated error; no false clear | TEST EXISTS |
| D10 | P1 | close called twice | idempotent underlying close | TEST EXISTS |
| D11 | P2 | full identifier appears in dependency text | normal formatter redacts it | TEST EXISTS in logging tests |

These tests mock the dependency boundary. They do not prove real `PreferredRsdTunnel`, DVT or LocationSimulation behavior on the user's phone.

Primary files: `tests/test_pymobiledevice_adapter.py`, `tests/test_logging.py`.

## 3. API contract regressions

| ID | Sev | Scenario | Expected | Coverage before local gate |
|---|---|---|---|---|
| A01 | P0 | connect fails | non-2xx stable envelope; never ready | TEST EXISTS |
| A02 | P0 | set fails | non-2xx `LOCATION_SET_FAILED`; never simulating | TEST EXISTS |
| A03 | P0 | clear fails | non-2xx; never claim ready | TEST EXISTS |
| A04 | P1 | set before connect | `INVALID_STATE`; adapter untouched | TEST EXISTS |
| A05 | P1 | latitude out of range | validation failure; no device call | TEST EXISTS |
| A06 | P1 | longitude out of range | validation failure; no device call | TEST EXISTS |
| A07 | P1 | NaN/non-finite coordinate | validation failure | TEST EXISTS |
| A08 | P1 | connect -> set -> status -> clear -> disconnect | authoritative state sequence | TEST EXISTS |
| A09 | P1 | health without phone/Internet dependency | health remains local-only | TEST EXISTS |
| A10 | P1 | fuel provider unavailable | device API remains functional | TEST EXISTS |
| A11 | P2 | unexpected internal exception | sanitized JSON `INTERNAL_ERROR`; no raw exception string | TEST EXISTS |
| A12 | P1 | presence probe proves selected device absent | status invalidates session | TEST EXISTS |
| A13 | P1 | presence probe cannot determine state | healthy cached session not destroyed from uncertainty alone | TEST EXISTS |

Primary files: `tests/test_api.py`, `tests/test_fuel_api.py`.

## 4. Fuel provider/service regressions

| ID | Sev | Scenario | Expected | Coverage before local gate |
|---|---|---|---|---|
| F01 | P1 | valid provider payload | normalized quotes | TEST EXISTS |
| F02 | P1 | connect timeout | two attempts total then unavailable | TEST EXISTS |
| F03 | P1 | read timeout | two attempts total then unavailable | TEST EXISTS |
| F04 | P1 | 5xx then success | one retry then current snapshot | TEST EXISTS |
| F05 | P1 | client 4xx | no retry; non-retryable unavailable | TEST EXISTS |
| F06 | P1 | malformed JSON | invalid-response error | TEST EXISTS |
| F07 | P1 | missing required schema fields | invalid-response error; no KeyError leak | TEST EXISTS |
| F08 | P1 | unknown fuel type | explicit no-quote result | TEST EXISTS |
| F09 | P2 | last-good cache then outage | stale snapshot explicitly marked | TEST EXISTS |
| F10 | P2 | outage with no usable cache | fuel API unavailable; device API unaffected | TEST EXISTS |
| F11 | P2 | provider coordinate out of range | response rejected | TEST EXISTS |

Primary files: `tests/test_fuel.py`, `tests/test_fuel_api.py`.

## 5. Local-server/browser security regressions

| ID | Sev | Scenario | Expected | Coverage before local gate |
|---|---|---|---|---|
| L01 | P0 | launcher listener | loopback only | TEST EXISTS |
| L02 | P1 | preferred port occupied | atomically reserve another loopback port; do not kill owner | TEST EXISTS |
| L03 | P1 | explicit port occupied | fail clearly; do not kill owner | TEST EXISTS |
| L04 | P1 | browser/static page | local JS/CSS served; no remote executable JS dependency | TEST EXISTS + source inspection |
| L05 | P1 | hostile/non-loopback Host | reject request | TEST EXISTS |
| L06 | P1 | cross-site browser mutation | reject before changing device state | TEST EXISTS |
| L07 | P1 | CSP | script/connect restricted to self; only OSM tile images allowed remotely | TEST EXISTS |
| L08 | P2 | browser hardening headers | nosniff/frame/referrer/permissions policy present | TEST EXISTS |
| L09 | P1 | external network unavailable | local health/device workflow must remain usable | HARDWARE/LOCAL ONLY |
| L10 | P1 | invalid TLS/provider certificate | TLS verification must remain enabled | DEPENDENCY/LOCAL CHECK; no code path disables verification |
| L11 | P2 | unexpected request fields | rejected without state corruption | TEST EXISTS |

The runtime also no longer creates a helper thread to launch the browser; the already-listening socket queues an early browser request until uvicorn starts accepting.

Primary files: `tests/test_bootstrap.py`, `src/geoportlocal/runtime/security.py`.

## 6. Browser/UI qualification

A browser automation framework is intentionally not added merely for this alpha. API tests prove server truth; the following are checked in the actual browser during local qualification.

| ID | Sev | Scenario | Expected |
|---|---|---|---|
| U01 | P0 | backend set fails | UI never shows success/simulating |
| U02 | P1 | partial metadata | discovered device remains selectable/understandable |
| U03 | P1 | disconnected | set/clear disabled |
| U04 | P1 | ready | set enabled; clear disabled |
| U05 | P1 | simulating | clear enabled; state visible |
| U06 | P1 | operation in progress | duplicate mutating actions disabled |
| U07 | P1 | fuel provider down | device controls remain usable |
| U08 | P2 | map tiles unavailable | coordinate entry and device controls remain usable |
| U09 | P2 | fuel quote selected | coordinates fill; device location is not applied automatically |

`src/geoportlocal/web/static/app.js` polls device status about every 2.5 seconds only while a session exists. It derives action availability from the latest server snapshot.

## 7. Hardware matrix

Record actual runs here. Never infer PASS from upstream documentation or committed unit tests.

| Host | Host version | Device | iOS | Connection | Discover | Connect | Set | Clear | 20x set/clear | Unplug recovery | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mac Apple Silicon | TBD | primary iPhone | 26.x | USB | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Mac Apple Silicon | TBD | available device | 18.x | USB | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |

Add rows only for hardware actually tested.

## 8. Ordered physical checks

### H01 — cold connect/set/clear

1. Launch GeoPortLocal with no phone; page and health must load.
2. Attach unlocked trusted iPhone by USB.
3. Refresh and connect.
4. Set a test coordinate.
5. Independently verify device-reported location changed.
6. Clear and verify real location resumes.
7. Disconnect.

Pass: UI state agrees with completed device operations and no restart is required.

### H02 — repeated lifecycle

Run 20 set/clear cycles, then five disconnect/reconnect cycles.

Pass: no progressive slowdown, stale connection, growing process/thread/socket count or address-in-use failure.

### H03 — unplug while READY

Connect to READY, unplug, wait for status polling, then reattach and reconnect.

Pass: old session is invalidated and a fresh connection is created without restarting GeoPortLocal.

### H04 — unplug while SIMULATING

Set location, unplug, observe the next status/operation, then reattach/reconnect.

Pass: GeoPortLocal does not retain a fake READY/SIMULATING session. Record what the phone does with the simulated location after physical transport loss; do not guess it.

### H05 — legacy coexistence and port collision

Keep legacy GeoPort installed. Exercise launch/quit order both ways and deliberately occupy preferred port 54321.

Pass: GeoPortLocal uses its own loopback listener/bundle identity and never kills/overwrites the other application.

### H06 — offline resilience

Disconnect Internet and use direct coordinates for the device workflow.

Pass: health/device controls continue; map tiles/fuel degrade without blocking local device operations.

### H07 — localhost browser boundary

With the local page open, confirm the browser console shows no CSP violation for normal operation and no remote script is loaded. Verify map tile requests are images from `tile.openstreetmap.org` only.

Pass: local UI works under the restrictive CSP.

## 9. Resource-leak observations

During local qualification capture before/after values where practical for:

- GeoPortLocal process count;
- child/native process count owned by the app;
- thread count;
- listening loopback ports;
- open descriptors/sockets.

Counts should return to a stable baseline after repeated lifecycle tests. Per-operation growth is a failure.

## 10. Release gate

Do not publish a GitHub Release because tests merely exist.

First private regular-use alpha requires:

- generated and committed `uv.lock`;
- `uv sync --locked`, Ruff and full pytest PASS on the target Mac;
- H01-H07 observed on the primary setup as applicable;
- no false-success result;
- no stale logical session after unplug/reconnect;
- legacy GeoPort preserved side-by-side;
- no unresolved P0/P1 in the declared primary matrix;
- limitations documented precisely.

Windows packaging/testing is a later gate and does not block the first private Mac alpha unless priority changes.

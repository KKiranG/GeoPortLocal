# GeoPortLocal regression and qualification matrix

Date: 2026-09-10

The purpose of this matrix is to prevent the modernization from reproducing the known failure modes of legacy GeoPort. Automated tests use fake adapters wherever possible. Hardware tests prove the real `pymobiledevice3` integration.

## 1. Severity

- **P0** — can leave device/application in an unsafe or unusable state, falsely reports a successful location operation, or corrupts/blocks future sessions.
- **P1** — core connect/set/clear workflow fails or leaks resources.
- **P2** — degraded diagnostics, fuel data, UI, packaging or compatibility.

A regular-use build requires zero open P0 defects and no unresolved P1 in the declared supported Mac/iOS matrix.

## 2. Unit tests — SessionManager

| ID | Severity | Scenario | Expected result |
|---|---|---|---|
| S01 | P0 | adapter connect raises | no connection cached; final local state disconnected; typed error returned |
| S02 | P0 | adapter returns partially constructed connection then raises | partial object closed; no session cached |
| S03 | P0 | set_location raises immediately | caller receives failure; state is not simulating |
| S04 | P0 | set_location transport disconnect | session invalidated and closed; state disconnected |
| S05 | P0 | clear_location transport disconnect | local resources still close; no stale session remains |
| S06 | P0 | connect timeout | operation cancelled/cleaned; no reusable session created |
| S07 | P0 | set timeout | no success response; connection classified according to adapter health/failure |
| S08 | P0 | two concurrent connect calls | mutation lock serializes/rejects second operation; never two owned sessions |
| S09 | P0 | set and clear submitted concurrently | deterministic serialization; state cannot become contradictory |
| S10 | P1 | clear while already READY | succeeds idempotently; no upstream set/clear call required unless contract requires it |
| S11 | P1 | disconnect while disconnected | succeeds idempotently |
| S12 | P1 | disconnect while ready | connection closes once; state disconnected |
| S13 | P1 | disconnect while simulating | clear attempted, close always attempted; state disconnected |
| S14 | P1 | clear fails during disconnect | close still executes; final state disconnected with diagnostic |
| S15 | P1 | reconnect after failed session | new adapter connection created; stale object never reused |
| S16 | P1 | 100 connect/disconnect cycles using fake adapter | live connection count returns to zero every cycle |
| S17 | P1 | 100 set/clear cycles | no task/resource count growth in fake adapter instrumentation |
| S18 | P2 | invalid transition e.g. set while disconnected | typed invalid-state error; no adapter call |

## 3. Unit tests — device adapter

These tests mock or fake the public dependency boundary rather than the HTTP layer.

| ID | Severity | Scenario | Expected result |
|---|---|---|---|
| D01 | P1 | USB device enumeration succeeds | stable `DeviceDescriptor` returned |
| D02 | P1 | device exists but metadata lookup fails | device is not silently dropped; descriptor/diagnostic reflects partial metadata |
| D03 | P1 | duplicate USB/network representations | deterministic selection/presentation; no duplicate session ownership |
| D04 | P1 | iOS >=17.4 | modern RSD connection path selected |
| D05 | P1 | iOS 17.0-17.3.1 before compatibility adapter exists | explicit `IOS_VERSION_UNSUPPORTED`/compatibility message, not a broken tunnel attempt |
| D06 | P1 | modern tunnel constructor fails | typed `TUNNEL_UNAVAILABLE`; all entered contexts unwound |
| D07 | P0 | DVT opens but LocationSimulation context fails | DVT and tunnel close; no connection returned |
| D08 | P0 | location `set()` raises | error translated; no success value |
| D09 | P0 | location `clear()` raises | error translated; no false clear claim |
| D10 | P1 | `close()` called twice | no crash; resources closed once/idempotently |
| D11 | P2 | full UDID appears in exception | normal logger redacts it before INFO/WARNING output |

## 4. API contract tests

All API tests run with `FakeDeviceAdapter`; they do not require a phone.

| ID | Severity | Request | Expected result |
|---|---|---|---|
| A01 | P0 | connect when fake adapter fails | non-2xx appropriate error + stable error envelope; never `ready` |
| A02 | P0 | POST location when fake set fails | non-2xx + `LOCATION_SET_FAILED`; never `simulating` |
| A03 | P0 | DELETE location when fake clear fails | non-2xx + `LOCATION_CLEAR_FAILED` or disconnect classification |
| A04 | P1 | POST location before connect | invalid-state response; adapter untouched |
| A05 | P1 | latitude > 90 | validation error; adapter untouched |
| A06 | P1 | longitude > 180 | validation error; adapter untouched |
| A07 | P1 | NaN/infinity coordinate | validation error |
| A08 | P1 | connect -> set -> status -> clear -> disconnect | states `ready -> simulating -> simulating -> ready -> disconnected` |
| A09 | P1 | health with no device and no Internet | health still `ok` |
| A10 | P1 | fuel provider unavailable | device API still passes all tests |
| A11 | P2 | unknown internal exception | sanitized `INTERNAL_ERROR`; raw stack not returned to browser |

Note: API test IDs use `Axx`; they are unrelated to any third-party application's A01/A09 codes.

## 5. Fuel provider tests

| ID | Severity | Scenario | Expected result |
|---|---|---|---|
| F01 | P1 | valid Project Zero Three payload | normalized quotes returned |
| F02 | P1 | HTTP connect timeout | `FUEL_PROVIDER_UNAVAILABLE`; one bounded retry only |
| F03 | P1 | HTTP read timeout | same as above |
| F04 | P1 | HTTP 500 then success | retry succeeds; response marked current |
| F05 | P1 | HTTP 400 | no retry unless provider contract says otherwise |
| F06 | P1 | malformed JSON | `FUEL_PROVIDER_INVALID_RESPONSE`; no crash |
| F07 | P1 | missing `regions` | validation failure, not KeyError leaking to UI |
| F08 | P1 | unknown/missing fuel-type entry | empty/not-found result with clear state |
| F09 | P2 | last-good cache exists and provider times out | cached response may be returned with `stale=true` |
| F10 | P2 | no cache and provider times out | fuel UI shows unavailable; device UI unaffected |
| F11 | P2 | coordinates outside valid ranges | provider response rejected |

## 6. Local-server/security tests

| ID | Severity | Scenario | Expected result |
|---|---|---|---|
| L01 | P0 | start application | server listens on loopback only by default |
| L02 | P1 | preferred port occupied | GeoPortLocal binds another free local port without killing existing process |
| L03 | P1 | old GeoPort process running | GeoPortLocal starts independently and does not terminate it |
| L04 | P1 | GeoPortLocal exits | old GeoPort remains alive |
| L05 | P1 | external network unavailable | local UI and device endpoints still load |
| L06 | P1 | TLS certificate invalid for fuel provider | request fails; TLS verification is not disabled |
| L07 | P2 | debug mode default | off |
| L08 | P2 | request contains arbitrary unexpected fields | ignored/rejected according to schema; no state corruption |

## 7. Browser/UI tests

Initial automation may use API-level tests plus a small browser smoke suite.

| ID | Severity | Scenario | Expected result |
|---|---|---|---|
| U01 | P0 | backend set fails | UI never shows successful/simulating state |
| U02 | P1 | device list metadata partial | discovered device remains visible with useful diagnostic |
| U03 | P1 | backend state disconnected | simulate/clear disabled |
| U04 | P1 | backend state ready | simulate enabled, clear disabled |
| U05 | P1 | backend state simulating | clear enabled and state visible |
| U06 | P1 | operation in progress | duplicate mutating clicks disabled |
| U07 | P1 | fuel provider down | map/device control remains usable |
| U08 | P2 | no Internet/map tile access | app still exposes coordinate entry and device controls rather than blank fatal page |

## 8. Hardware smoke matrix

Record each actual run here. Do not infer support from upstream docs alone.

Columns to complete during local work:

| Host | Host version | Device | iOS | Connection | Discover | Connect | Set | Clear | 20x set/clear | Unplug recovery | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mac Apple Silicon | TBD | primary iPhone | 26.x | USB | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Mac Apple Silicon | TBD | available device | 18.x | USB | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |

Add rows only for hardware actually tested.

## 9. Mandatory physical test scripts

### H01 — cold connect

1. Quit GeoPortLocal.
2. Ensure old GeoPort may remain installed but is not controlling the same device.
3. Attach trusted iPhone via USB.
4. Launch GeoPortLocal.
5. Discover.
6. Connect.
7. Set a test coordinate.
8. Verify with a neutral device-side location display suitable for testing.
9. Clear.
10. Verify real device location resumes.
11. Disconnect.

Pass: every UI state agrees with the actual device operation; no manual restart required.

### H02 — repeated lifecycle

Run 20 cycles:

```text
set coordinate A
clear
set coordinate B
clear
```

Then disconnect/reconnect five times.

Pass:
- no progressive slowdown;
- no growing console spam;
- no address-in-use error;
- no stale-session reuse;
- no application restart required.

### H03 — unplug during READY

1. Connect until READY.
2. Physically unplug device.
3. Request status / attempt set.
4. Reattach device.
5. Rediscover and reconnect.

Pass: old session is invalidated; reconnect creates a new connection and succeeds without restarting GeoPortLocal.

### H04 — unplug while SIMULATING

1. Connect.
2. Set location successfully.
3. Unplug device.
4. Observe state.
5. Reattach.
6. Reconnect.
7. Clear if the OS still reports simulation active.

Pass: GeoPortLocal does not retain a fake READY/SIMULATING session after transport loss.

### H05 — old GeoPort coexistence

1. Keep existing legacy application installed.
2. Launch/quit old GeoPort.
3. Launch GeoPortLocal.
4. Repeat in the reverse order, but never ask both programs to own the same device session simultaneously.

Pass: neither application kills the other by process-name matching; bundle/config/log paths do not overwrite each other.

### H06 — offline resilience

1. Disconnect Mac from Internet.
2. Launch GeoPortLocal.
3. Discover/connect/set/clear using USB.
4. Open fuel view.

Pass: device functions work; fuel view reports provider unavailable/stale; app does not hang on IP geolocation, GitHub broadcast, fuel or map requests.

## 10. Resource-leak checks

During local qualification capture before/after values for:

- GeoPortLocal process count;
- Python/native child process count owned by the app;
- thread count;
- asyncio task count in debug diagnostics;
- listening loopback ports;
- open file descriptors/sockets where practical.

After repeated lifecycle tests, counts should return to a stable baseline. A bounded cache or server worker may remain; per-operation growth is a failure.

## 11. Release gate

Do not publish a GitHub Release merely because unit tests pass.

First usable local alpha requires:

- all automated P0/P1 tests passing;
- H01-H06 completed on the primary Mac/iPhone pair;
- no false-success case;
- no stale session after unplug/reconnect;
- old GeoPort preserved side-by-side;
- known limitations documented.

Windows packaging/testing is a separate gate and does not block the first private Mac alpha unless the founder changes priority.
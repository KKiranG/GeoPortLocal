# GeoPortLocal research baseline — September 2026

Date: 2026-09-10

This note records external facts that materially affect the modernization. It is not an implementation guide for bypassing third-party controls.

## 1. Sources examined

### GeoPort / upstream

- Fork: https://github.com/KKiranG/GeoPortLocal
- Upstream: https://github.com/davesc63/GeoPort
- Upstream latest release: https://github.com/davesc63/GeoPort/releases/tag/v4.0.2
- Upstream issue tracker, especially device connection, stale tunnel, iOS 18/26, packaging and location reset reports.

### Current iOS transport dependency

- pymobiledevice3: https://github.com/doronz88/pymobiledevice3
- Current release examined: v11.12.1, published 2026-09-09.
- Python API guide: https://github.com/doronz88/pymobiledevice3/blob/master/docs/guides/python-api.md
- iOS 17+ tunnel guide: https://github.com/doronz88/pymobiledevice3/blob/master/docs/guides/ios17-tunnels.md
- Current location simulation service and CLI implementation.

### Fuel / 7-Eleven

Primary current official sources:

- My 7-Eleven terms: https://www.7eleven.com.au/mobile/Terms-and-Conditions.html
- Fuel Price Lock terms: https://www.7eleven.com.au/mobile/my-7-eleven-app-fuel-price-lock-terms-and-conditions.html
- My 7-Eleven FAQ: https://www.7eleven.com.au/my-7-eleven/my-7-eleven-faqs.html

Primary community source:

- OzBargain, “7-Eleven Fuel App Watch - Nationwide”: https://www.ozbargain.com.au/node/678629
- Relevant recent/current pages examined include `?page=57`, `?page=58`, `?page=59` and later indexed pages through `?page=62`, plus historical comments surfaced by targeted searches for GeoPort, A01 and A09.

Secondary community sources:

- Reddit/AusFinance and Australian fuel/frugal discussions, including August 2026 discussion of Fuel Lock geographic behaviour and current account-risk anecdotes.

### Agent workflow / Astra

- OpenAI GPT-6 Astra announcement: https://openai.com/index/gpt-6-astra/
- OpenAI GPT-6 Astra model guidance: https://developers.openai.com/api/docs/guides/latest-model
- OpenAI Codex documentation index and AGENTS.md guidance: https://developers.openai.com/
- OpenAI Codex usage guidance: https://help.openai.com/en/articles/11369540-codex-and-chatgpt-plan-usage-limits
- X was searched for current Astra/Codex discussion; search indexing exposed official OpenAI Developers presence and recent Codex discussion, but architectural decisions below rely on official OpenAI documentation rather than X summaries.

### Packaging

- PyInstaller 6.22.2 docs/changelog: https://pyinstaller.org/en/stable/CHANGES.html
- PyInstaller security advisories: https://github.com/pyinstaller/pyinstaller/security

## 2. Repository facts

The fork is not a separately evolved implementation. Its current tree and commit history closely match upstream. The application source is concentrated in `src/main.py`, with two very large HTML templates.

The checked-in source has several characteristics that explain observed failures:

1. **Global connection state.** `udid`, `connection_type`, `ios_version`, `lockdown`, `rsd_host`, `rsd_port`, `rsd_data` and related values are process globals.
2. **Manual tunnel ownership.** The application explicitly starts TCP/QUIC tunnel threads and stores host/port results.
3. **Invalid session caching.** `connect_usb()` can reach the tunnel timeout with no RSD address, continue, and store `{"host": None, "port": None}` in `rsd_data_map`.
4. **False-success path.** `/set_location` starts a background thread and then returns `Location set successfully`; errors can occur later inside the thread.
5. **Thread proliferation.** each `start_set_location_thread` creates both a location thread and a termination-check thread. The global flag is shared between all of them.
6. **Pseudo-termination.** `terminate_threads()` creates new `threading.Event()` objects and sets those new objects; it does not terminate the already running threads.
7. **Blocking calls inside async code.** the location coroutine contains `time.sleep()` loops.
8. **Network exposure.** Flask runs with `host='0.0.0.0'` and debug enabled in source.
9. **TLS bypass.** some requests are made with `verify=False` and urllib3 certificate warnings are suppressed.
10. **Unrelated external dependency during normal UI load.** country discovery can fall back to an unencrypted `ip-api.com` request.
11. **Private/internal dependency coupling.** application code imports multiple `pymobiledevice3.cli.*` modules rather than only a small stable library adapter.
12. **No reproducible dependency/build definition in the repository.** This makes the release binary difficult to reproduce from the visible source.

The current upstream release is v4.0.2 from December 2024. The committed `src/main.py` under that release lineage still contains `APP_VERSION_NUMBER = "2.3.3"`, another sign that repository source, release metadata and packaged application history are not cleanly aligned.

## 3. Upstream issue evidence

Several upstream reports map directly to the source defects above.

### Invalid RSD state is real

Issue #108 shows a device detected correctly on iOS 17.6.1, then a USB TCP tunnel fails to establish. The application logs `RSD Data is None`, stores host/port as `None`, and on the next attempt reports the invalid object as an already-created connection. Subsequent location attempts fail with name-resolution errors.

Source: https://github.com/davesc63/GeoPort/issues/108

Conclusion: session reuse must be based on a live owned provider/session, never merely the presence of a dictionary entry.

### External startup call can interfere with the app

Issue #182 in February 2026 shows IP-geolocation timeouts during startup/use.

Source: https://github.com/davesc63/GeoPort/issues/182

Conclusion: Internet-dependent locale detection must be removed from the device path.

### iOS 26 discovery/UI mismatch

Issue #189 in June 2026 shows iOS 26.4.2 detected as a raw USB device but not becoming usable/selectable in the UI.

Source: https://github.com/davesc63/GeoPort/issues/189

Conclusion: device discovery, metadata loading and UI presentation need separate states/errors. One slow/failing metadata operation must not convert a physically discovered device into an empty UI without explanation.

### “success” can be untrue

Historical issues including #102, #141 and #145 show cases where the UI/log reports success or proceeds even though location simulation fails immediately afterward.

Conclusion: asynchronous fire-and-forget around a user-facing mutating operation is not acceptable. The HTTP/API response must await the set/clear operation.

### Persistent simulated location after disconnect is not a stable application contract

Numerous issues report different persistence behaviour across iOS 17, 18 and 26 after cable/tunnel disconnect.

Conclusion: GeoPortLocal will guarantee its operation only while it owns a valid developer-service session. Persistence after transport teardown is treated as OS-dependent behaviour, not something the application promises or attempts to force.

## 4. What changed in pymobiledevice3

This is the most important technical modernization finding.

`pymobiledevice3` v11.12.1 was released on 2026-09-09 and is actively maintained. Its current Python API is asyncio-based and exposes a materially simpler connection model than the old GeoPort implementation.

### Current recommended developer-service connection

The current Python API guide says that for developer/DVT services on iOS 17+, library consumers should normally use `PreferredRsdTunnel`.

`PreferredRsdTunnel`:

- is an async context manager;
- selects the preferred no-root transport;
- uses the native `remoted` path on macOS where possible;
- uses the in-process userspace tunnel on other platforms;
- falls back appropriately;
- yields a connected `RemoteServiceDiscoveryService`.

The current tunnel guide states that iOS 17.4+ is supported over USB without root/admin on the normal modern path. iOS 17.0-17.3.1 is a special case and normally routes through privileged `tunneld`.

### Current location API

The current location implementation uses:

```python
async with DvtProvider(service_provider) as dvt, LocationSimulation(dvt) as location_simulation:
    await location_simulation.set(latitude, longitude)
```

and clear is similarly awaited.

This means the modernization can remove the old pattern of manually exposing an RSD host/port to the rest of the application.

### Dependency support

The v11.12.1 `pyproject.toml` declares Python >=3.9 and classifiers through Python 3.15. Python 3.14 is therefore a conservative current baseline for GeoPortLocal rather than selecting a beta/newest interpreter merely because it exists.

## 5. OzBargain / community findings

Community reports are evidence of symptoms, not proof of 7-Eleven's server implementation. They must not be converted into invented claims about specific anti-fraud signals.

### The main OzBargain thread is the key knowledge source

The Nationwide Fuel App Watch thread is the long-running centre of community knowledge. Its current header still lists GeoPort as an iOS method and explicitly notes that GeoPort has not had a release update since December 2024 and that users report varying success/failure.

Recent relevant comments show a consistent distinction between **device location simulation working** and **Fuel Lock acceptance failing**.

Examples found in the thread:

- September/October 2025: users report iOS 26 + GeoPort working at the phone-location layer, while A01 outcomes vary between users and network conditions.
- March 2026: users report GeoPort or 3uTools successfully changing device location while interstate Fuel Lock attempts produce A01; some report same-state locks still working.
- April/May 2026: A01 is also reported in some same-state cases, showing that A01 is not a clean “interstate spoof detected” diagnostic.
- May 2026: a user explicitly reports previous accounts receiving A09 and suspects interstate locking as the reason, while another reports interstate success. These are anecdotes, not enough to establish a deterministic rule.
- May 27 2026: one Android report states that a VIC-from-NSW attempt produced A01 while NSW-from-NSW worked.
- Other reports show temporary service outages, login problems and normal Fuel Lock instability independent of GeoPort.

The result is important: **do not design GeoPortLocal around A01.** A01 is an external application outcome with multiple observed causes/contexts. GeoPortLocal can and should diagnose its own connection and simulation result, but it cannot truthfully label A01 as a GeoPort transport failure.

### Current August 2026 evidence

An August 3 2026 AusFinance discussion still contains users saying nationwide spoofing is now risky/inconsistent and others saying same-state use continues to work for them. It also contains warnings about account bans.

This is current enough to reinforce the same conclusion: third-party acceptance is not a stable client-side contract.

## 6. Official 7-Eleven facts that affect project claims

Current 7-Eleven terms were checked on 2026-09-10.

They state that:

- Fuel Lock requires access to device location;
- the app normally considers up to five closest eligible 7-Eleven stores within 250 km;
- Best Local Price can fail because of communication/system issues;
- checks are rate-limited to prevent abuse;
- account/device/use restrictions exist;
- users must not manipulate the location information reported by the device when using the app, including manipulation available under developer options;
- 7-Eleven may suspend or cancel an account when it reasonably suspects location manipulation.

Therefore the project documentation must not promise “undetectable”, “A01-free”, “interstate lock support”, or equivalent third-party outcomes.

The official terms also provide an engineering lesson: normal 7-Eleven backend/system problems can make Fuel Lock unavailable. GeoPortLocal diagnostics must avoid attributing external app failures to the local simulator without evidence.

## 7. Fuel-price data source findings

The legacy app uses:

`https://projectzerothree.info/api.php?format=json`

The OzBargain Fuel App Watch thread still lists Project Zero Three as a primary fuel-price resource in 2026, so it remains valuable.

However:

- GeoPortLocal does not own its schema or availability;
- historical community comments report occasional source/station/state data anomalies;
- a provider outage must not stop device control;
- an external schema change should fail at one adapter boundary, not throughout the UI.

Decision: keep Project Zero Three initially, but isolate it behind `FuelProvider` and validate/normalize responses.

## 8. Packaging findings

PyInstaller is actively maintained; 6.22.2 was released 2026-08-17 and Python 3.14/3.15 are supported by recent releases.

A high-severity PyInstaller local-privilege-escalation advisory was published in August 2026 affecting privileged executable scenarios.

This strengthens two decisions:

1. GeoPortLocal should not run its entire application bundle elevated merely because legacy tunnel code did.
2. Packaging versions must be pinned and security-reviewed when changed.

The normal macOS + iOS 17.4+ path in current `pymobiledevice3` no longer requires the old blanket sudo model.

## 9. Astra / Codex findings

GPT-6 Astra was released 2026-09-03 and is being rolled into Codex. OpenAI's current help documentation says Astra requires Codex CLI 0.153.0 or newer.

OpenAI's current model guidance matters directly to repository structure:

- Astra is stronger at instruction following and can be more sensitive to instructions in `AGENTS.md`, skills and other instruction files.
- OpenAI recommends auditing accessible instruction files for conflicting guidance.
- Codex usage varies with task/codebase size and complexity; larger, long-running tasks that require more context consume more allowance.
- Codex supports project `AGENTS.md`; its instruction chain can also include narrower directory-level guidance depending on launch location.

Decision for GeoPortLocal:

- keep root `AGENTS.md` concise;
- put durable architecture/research/test detail in separate docs;
- have `AGENTS.md` route an agent to one relevant doc rather than telling it to read all docs every turn;
- do not paste the full OzBargain research corpus or third-party API docs into `AGENTS.md`;
- split implementation into bounded work packages;
- use subagents only when they can inspect genuinely different evidence in parallel;
- prefer targeted tests/reads over repo-wide review every turn.

X was searched as requested, but no X post should override current OpenAI product/docs guidance. Search-indexed X results were mostly discussion summaries; official OpenAI documentation is the stronger source for implementation decisions.

## 10. Decisions derived from the research

1. Keep the product name **GeoPortLocal**.
2. Keep `main` as a legacy baseline; modernize on a separate branch.
3. Keep the old downloaded GeoPort installed during development.
4. Package the new program as a separate `GeoPortLocal.app`.
5. Do not patch the legacy RSD host/port/thread design into another generation.
6. Use a project-owned adapter over current `pymobiledevice3` public APIs.
7. Use `PreferredRsdTunnel` for the normal iOS 17.4+ developer-service path.
8. Use `DvtProvider` + awaited `LocationSimulation.set/clear`.
9. Use one device-session owner and explicit state machine.
10. Never cache invalid/incomplete sessions.
11. Never return location success before the device call completes.
12. Bind the local server to loopback only.
13. Remove external IP geolocation from the critical path.
14. Keep Project Zero Three, but only behind a validated provider boundary.
15. Do not engineer or claim A01/A09 avoidance.
16. Make third-party acceptance explicitly outside GeoPortLocal's health model.
17. Target Python 3.14 for the first reproducible development environment.
18. Keep agent instructions lean and task-scoped for Astra/Codex efficiency.

## 11. Freshness notes

Sources less than 90 days old as of 2026-09-10 include:

- pymobiledevice3 v11.12.1 — 2026-09-09;
- GPT-6 Astra launch/guidance — September 2026;
- PyInstaller 6.22.x — August 2026;
- August 2026 Australian Reddit Fuel Lock discussion;
- current 7-Eleven terms/FAQ pages as crawled/checked September 2026.

The most relevant OzBargain behavioural comments are primarily March-May 2026 and are therefore now more than 90 days old. They remain useful as historical issue evidence but must not be represented as proof of today's 7-Eleven backend behaviour. Before making a future architectural decision based on A01/A09/community behaviour, repeat the targeted web search and append a new dated research note.
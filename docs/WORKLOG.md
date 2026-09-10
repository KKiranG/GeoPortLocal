# GeoPortLocal worklog

Keep this file short. It is the handoff for a fresh local agent, not a history archive.

## Current status

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Phase: GitHub-side implementation/reconciliation complete; target-Mac execution and real-device/package qualification pending  
Definitive next-run plan: `docs/HERMES_LOCAL_HANDOFF.md`  
Legacy fallback: `main`, legacy runtime/templates and the installed legacy GeoPort application remain untouched

## Implemented on this branch

- Python 3.14 `uv` project metadata with `pymobiledevice3==11.12.1` and pinned PyInstaller development dependency;
- FastAPI/uvicorn loopback-only runtime and atomic alternate-port fallback without killing an existing owner;
- project-owned `PreferredRsdTunnel -> DvtProvider -> LocationSimulation` adapter boundary;
- one serialized `SessionManager` with awaited set/clear, fresh-session recovery and no reusable failed connection;
- READY-state explicit recovery Clear because local READY does not prove an earlier process left no device-side simulation;
- normal live READY/SIMULATING disconnect/shutdown performs recovery clear before close; positively confirmed physical absence skips impossible clear and invalidates stale ownership;
- bounded two-second presence probe under the same session mutation lock, so uncertainty preserves the session and stale probe results cannot race a reconnect;
- disconnect cleanup failure tears down local ownership but returns a non-success API error rather than false success;
- canonical typed/sanitized API errors including generic `INTERNAL_ERROR` for unexpected exceptions;
- strict coordinate/fuel normalization and isolated Project Zero Three provider with TLS verification, bounded retry and stale last-good semantics;
- local HTML/CSS/JavaScript UI with no remote executable JavaScript and optional OSM image tiles;
- local Host validation, exact-origin mutation protection, restrictive CSP, authoritative HTML/API `no-store`, and OSM-compatible `strict-origin-when-cross-origin` referrer policy;
- bounded rotating redacted diagnostics at `~/Library/Logs/GeoPortLocal/geoportlocal.log` on macOS;
- no browser-launch helper thread;
- PyInstaller side-by-side `GeoPortLocal.app` spec;
- expanded session/API/adapter/fuel/security/logging/startup regression coverage;
- definitive autonomous local execution plan in `docs/HERMES_LOCAL_HANDOFF.md`, with Codex/Astra reserved for bounded delegation only.

## Evidence boundary — still unverified

Do **not** convert these to PASS from repository inspection:

1. generation/review of `uv.lock` and full Python 3.14 resolution on the target Mac;
2. `uv sync --locked`, Ruff, full pytest and optional local Node syntax check;
3. real USB discovery, Trust and Developer Mode behavior;
4. real `PreferredRsdTunnel`, DVT and `LocationSimulation` set/clear/recovery-clear behavior;
5. physical unplug/reconnect and quit-while-simulating observations;
6. whether a Developer Disk Image step is needed on this actual phone — investigate only if DVT evidence points there;
7. live Project Zero Three response compatibility and offline degradation;
8. real-browser CSP/origin/cache/OSM behavior;
9. `dist/GeoPortLocal.app` freezing, launch, persistent logging, shutdown/relaunch, Apple Silicon and Gatekeeper behavior;
10. side-by-side operation with the installed legacy GeoPort on the actual Mac.

## Next action

Do not perform another broad repo review. In the existing local clone, execute `docs/HERMES_LOCAL_HANDOFF.md` from Phase 0 through Phase 9. Start by preserving any local user changes, sync this branch, create the lockfile, and run the deterministic fast gate. Fix only failures demonstrated by local evidence.

Normal coding workers handle mechanical work. Escalate only an already-reproduced difficult tunnel/DVT/lifecycle issue to Astra. Use one focused independent final review after substantive local runtime fixes; no review swarm.

Update only actually observed rows in `docs/TEST_MATRIX.md`, keep `TEST EXISTS` distinct from PASS, commit/push evidence-backed local fixes to this branch, and leave merge/release as a separate founder decision.

## Failure classification

```text
bootstrap/dependency
-> usbmux discovery/metadata
-> trust/developer mode
-> PreferredRsdTunnel
-> DVT/LocationSimulation or demonstrated DDI dependency
-> SessionManager/presence ownership
-> API/security middleware
-> browser UI
-> fuel provider
-> packaging
```

Do not reopen legacy files or broad research unless the observed failure specifically requires comparison.

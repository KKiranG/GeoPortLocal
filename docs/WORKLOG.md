# GeoPortLocal worklog

Keep this file short. It is the handoff for a fresh Codex/Astra session, not a history archive.

## Current status

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Phase: planning complete; implementation not yet started  
Legacy fallback: `main` and the user's existing downloaded GeoPort installation remain untouched

## Completed

- Researched fork/upstream structure and known failure modes.
- Researched current OzBargain Fuel App Watch discussion and recent Australian community reports.
- Verified current 7-Eleven terms/FAQ relevant to location and Fuel Lock behaviour.
- Verified `pymobiledevice3` v11.12.1 current async Python API and iOS 17+ tunnel guidance.
- Verified current PyInstaller and Astra/Codex guidance.
- Added root `AGENTS.md`.
- Added `docs/MASTER_PLAN.md`.
- Added `docs/RESEARCH_2026-09.md`.
- Added `docs/ARCHITECTURE.md`.
- Added `docs/TEST_MATRIX.md`.
- Added `docs/AGENT_WORKFLOW.md`.

## Key decisions

- Product remains **GeoPortLocal**.
- New app must coexist with old GeoPort; never overwrite/kill the old app.
- Python 3.14 development baseline.
- FastAPI/uvicorn local async backend; plain HTML/JS/Leaflet frontend.
- Use a project-owned device adapter over current public `pymobiledevice3` APIs.
- iOS 17.4+ modern path uses `PreferredRsdTunnel` + `DvtProvider` + `LocationSimulation`.
- One `SessionManager` owns device state/lifecycle.
- No raw RSD host/port caching in application state.
- Project Zero Three retained initially behind `FuelProvider`.
- Third-party anti-abuse/A01/A09 evasion is outside project scope.

## Next work package

**WP1 — reproducible project bootstrap without changing legacy runtime**

Create:

- `pyproject.toml`
- `.python-version`
- `src/geoportlocal/__init__.py`
- `src/geoportlocal/__main__.py`
- initial package/version metadata
- test skeleton and minimal health/import test

Constraints:

- do not edit `src/main.py` or legacy templates in WP1;
- use Python 3.14;
- set up `uv`-compatible dependency metadata;
- direct dependencies must be explicit even if currently transitive through `pymobiledevice3`;
- do not generate/publish a release;
- lockfile generation and executing tests should be done locally after sync if the GitHub-only environment cannot run `uv` reliably.

## Hardware/user blocker

None for WP1.

Real iPhone access becomes necessary when the new `pymobiledevice3` adapter reaches hardware qualification.
# GeoPortLocal worklog

Keep this file short. It is the handoff for a fresh Codex/Astra session, not a history archive.

## Current status

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Phase: hardware-independent implementation complete; local Python 3.14 and real-device qualification pending  
Legacy fallback: `main`, legacy `src/main.py`/templates and the user's existing downloaded GeoPort installation remain untouched

## Implemented on this branch

- concise root `AGENTS.md` and separate architecture/research/test/handoff docs;
- Python 3.14 `pyproject.toml` with current pinned `pymobiledevice3==11.12.1`;
- FastAPI/uvicorn loopback-only application core;
- one serialized `SessionManager` with no reusable failed session and no optimistic location success;
- real modern adapter boundary: `PreferredRsdTunnel -> DvtProvider -> LocationSimulation`;
- iOS 17.4+ first-version gate and typed dependency error translation;
- idle disconnect presence probe without a resident watcher thread;
- canonical `/api/devices`, `/api/device/*`, `/api/location` and `/api/fuel/*` contracts;
- Project Zero Three provider with TLS verification, bounded timeout/retry, schema validation, 60-second fresh cache and explicit stale last-good fallback;
- browser UI using local HTML/CSS/JavaScript only; external map content is image tiles, not remote executable JavaScript;
- map click/zoom + coordinate entry + fuel quote coordinate selection;
- normal log redaction for iOS identifiers;
- safe startup: prefer 54321, otherwise reserve another loopback port; never kill the existing port owner;
- PyInstaller macOS `GeoPortLocal.app` spec and guarded bootstrap/check/build scripts;
- fake-adapter/session/API/fuel/startup/redaction/adapter-contract tests.

## Not yet verified — do not mark PASS from repository inspection

1. `uv lock` and the complete dependency resolution under Python 3.14 on the user's Mac.
2. `uv run ruff check .` and the full suite in that locked environment after this final GitHub pass.
3. Real USB discovery/trust and Developer Mode behavior on the target iPhone.
4. Real `PreferredRsdTunnel`, DVT location set/clear and unplug/reconnect behavior.
5. Current live Project Zero Three payload compatibility.
6. `dist/GeoPortLocal.app` freezing, launch, shutdown, relaunch and Apple Silicon behavior.
7. macOS signing/Gatekeeper behavior if the bundle is moved outside the build tree.

## Next action

Do not start another architecture review. Sync the branch locally once and run **Session 1** in `docs/CODEX_HANDOFF.md`:

```text
uv lock -> uv sync --locked -> Ruff -> full pytest
```

Commit `uv.lock` plus only genuine fixes revealed by that gate. Then run the real-device qualification in `docs/LOCAL_BOOTSTRAP.md` and update only the hardware rows actually observed in `docs/TEST_MATRIX.md`.

## Failure rule

A local/hardware failure should be classified to the smallest layer before changing code:

```text
bootstrap/dependency
-> usbmux discovery/metadata
-> trust/developer mode
-> PreferredRsdTunnel
-> DVT/LocationSimulation
-> SessionManager/API
-> browser UI
-> fuel provider
-> packaging
```

Do not reopen legacy files or broad research unless the observed failure specifically needs comparison.

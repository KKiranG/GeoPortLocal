# GeoPortLocal worklog

Keep this file short. It is the handoff for a fresh local agent, not a history archive.

## Current status

Date: 2026-09-10  
Branch: `geoportlocal-modernization`  
Phase: Hermes Local Execution (Phases 0–9) completed on target Mac (Apple Silicon M2 / macOS 26.5.1)  
Definitive next-run plan: `docs/HERMES_LOCAL_HANDOFF.md`  
Legacy fallback: `main`, legacy runtime/templates and the installed legacy GeoPort application remain untouched

## Verified on target Mac

1. **Python 3.14 locked baseline**: `uv.lock` generated with pinned `pymobiledevice3==11.12.1` and `pyinstaller==6.22.2`;
2. **Quality gates**: `uv sync --locked`, Ruff (`All checks passed!`), pytest (`71 passed`), and Node JS syntax check all passed;
3. **Localhost boundary**: Loopback-only binding, atomic fallback on occupied port 54321 without terminating owner, explicit busy port rejection;
4. **Browser security**: Local JS/CSS, no remote executable JS, strict CSP, `Cache-Control: no-store` on HTML/API, and OSM-compatible `strict-origin-when-cross-origin` referrer policy;
5. **Live fuel & offline degradation**: Project Zero Three live API successfully fetched 102 quotes and normalized; offline degradation confirmed device controls remain operational during network outage;
6. **Packaged bundle**: `dist/GeoPortLocal.app` (Apple Silicon arm64, bundle ID `io.github.kkirang.geoportlocal`) built via PyInstaller, verified launch, loopback serving, static assets, health, device discovery, fuel, persistent logging, and clean shutdown;
7. **Coexistence**: Installed legacy `/Applications/GeoPort-mac.app` (`org.davesc63.GeoPort`) and port 54321 owner (`com.docker`) coexisted untouched;
8. **Logging**: Bounded rotating redacted persistent logs verified at `~/Library/Logs/GeoPortLocal/geoportlocal.log`.

## Evidence boundary — remaining hardware requirement

- **H01–H04 physical device tests**: BLOCKED / PENDING HARDWARE. During autonomous execution on this MacBook Air (M2, macOS 26.5.1), `pymobiledevice3 usbmux list` returned empty (`[]`). A physical unlocked iPhone running iOS 17.4+ with Developer Mode enabled must be attached via USB to run the physical qualification steps.

## Next action

Connect physical iPhone via USB, launch `dist/GeoPortLocal.app` (or `uv run geoportlocal`), and execute physical test sequence H01–H04. Merge to `main` and release remain separate founder decisions.

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

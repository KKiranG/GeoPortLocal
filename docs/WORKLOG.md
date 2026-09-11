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
5. **Live fuel & degradation isolation**: Project Zero Three exposed 18 regions and 6 NSW fuel types and returned a normalized current quote; a process-local upstream outage returned `FUEL_PROVIDER_UNAVAILABLE` while health and device discovery remained available;
6. **Packaged bundle**: `dist/GeoPortLocal.app` (Apple Silicon arm64, bundle ID `io.github.kkirang.geoportlocal`) built via PyInstaller, verified launch, loopback serving, static assets, health, device discovery, fuel, persistent logging, and clean SIGTERM shutdown; the private ad-hoc build is rejected by `spctl`, and AppleScript quit did not stop the windowed process;
7. **Coexistence**: Installed legacy `/Applications/GeoPort-mac.app` (`org.davesc63.GeoPort`) and port 54321 owner (`com.docker`) coexisted untouched;
8. **Logging**: Bounded rotating redacted persistent logs verified at `~/Library/Logs/GeoPortLocal/geoportlocal.log`.

## Evidence boundary — remaining hardware requirement

- **H01–H04 physical device tests**: BLOCKED / PENDING USB HARDWARE. During autonomous execution on this MacBook Air (M2, macOS 26.5.1), `pymobiledevice3 usbmux list` exposed a network-only iPhone representation running iOS 26.6.1, but no USB transport was attached. No connect, DVT, recovery-clear, set/clear or unplug lifecycle command was attempted, and the conditional DDI diagnostic was not triggered.
- **H06 complete offline phone workflow**: PARTIAL. Process-local fuel-provider outage isolation passed, but actual Internet disconnection plus direct-coordinate operation on a connected phone remains unobserved.
- **Windowed package quit**: AppleScript quit returned success without terminating the private bundle; SIGTERM shut it down cleanly. This is a packaging/lifecycle characterization, not a device-runtime result.

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

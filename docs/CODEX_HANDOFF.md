# Codex / Astra supporting handoff

Date: 2026-09-10  
Branch: `geoportlocal-modernization`

The definitive local execution plan is now `docs/HERMES_LOCAL_HANDOFF.md`. Use this file only when a local Hermes phase delegates a bounded coding/diagnostic package to Codex/Astra.

Read root `AGENTS.md`, the relevant phase in `docs/HERMES_LOCAL_HANDOFF.md`, and only the target source/tests. Do not rescan the whole legacy repository.

## Mechanical environment/test work

Use normal Codex for deterministic work such as lock generation, Ruff, pytest, JavaScript syntax checking and straightforward fixes.

```text
Work only in KKiranG/GeoPortLocal on branch geoportlocal-modernization.
Read AGENTS.md and the current phase in docs/HERMES_LOCAL_HANDOFF.md.

Goal: fix the already-observed local gate failure without redesigning the project.

Reproduce the exact failing command, inspect only the target files and adjacent tests, implement the smallest evidence-backed fix, run the targeted check, then run bash scripts/check.sh. If app.js changed and Node is already installed, also run node --check src/geoportlocal/web/static/app.js.

Do not upgrade dependencies, add features, alter the legacy app, weaken security/log redaction, or broaden compatibility without evidence. Report exact commands/results and files changed.
```

## Real device integration work

Start with normal Codex. Escalate to Astra only after a reproducible `pymobiledevice3`/DVT/session-lifecycle failure remains genuinely ambiguous.

```text
Continue on geoportlocal-modernization. Read AGENTS.md, the relevant hardware phase in docs/HERMES_LOCAL_HANDOFF.md, the smallest redacted failure evidence, the target device/session module and adjacent tests.

Classify the failure first: usbmux metadata, trust/developer mode, PreferredRsdTunnel, DVT/LocationSimulation, DDI availability, SessionManager/presence ownership, API/UI, or packaging. Fix only the demonstrated layer. Preserve truthful completion semantics and fresh-session recovery. Add the narrowest regression test and rerun bash scripts/check.sh plus the affected hardware scenario.
```

### Astra escalation

```text
Use Astra only for this already-reproduced GeoPortLocal integration failure. Do not perform a broad review.

Read AGENTS.md, the redacted failure evidence, the target module/tests, and the relevant architecture/test-matrix section. Determine whether the pinned pymobiledevice3 assumption is wrong on this Mac/iPhone or GeoPortLocal owns the lifecycle incorrectly. Produce the smallest evidence-backed fix, targeted regression, full fast-gate result and exact remaining hardware observation. No unrelated refactor.
```

## Intentional runtime decisions

Do not redesign these without observed evidence:

- Python 3.14 baseline;
- FastAPI/uvicorn loopback-only backend;
- local HTML/CSS/JavaScript UI;
- one `SessionManager` and one mutation lock;
- `PreferredRsdTunnel -> DvtProvider -> LocationSimulation` for modern iOS;
- explicit Clear allowed from READY as a stale-simulation recovery command;
- bounded presence probing: uncertainty preserves the session, confirmed absence invalidates it;
- Project Zero Three isolated behind a provider/service boundary;
- exact-origin browser mutation protection plus local Host validation;
- restrictive CSP and `no-store` for authoritative HTML/API state;
- OSM image tiles only, with `strict-origin-when-cross-origin` rather than suppressed Referer;
- bounded redacted persistent logs under GeoPortLocal's own user log directory;
- preferred port 54321 with atomic alternate loopback reservation;
- installed legacy GeoPort remains untouched as fallback.

## DDI rule

Do not automatically add Developer Disk Image mounting. Only investigate it when a real DVT failure specifically points there. The local handoff contains the diagnostic command and acceptance rule.

## Review rule

After substantive runtime fixes, use one independent strong review focused only on false success, stale-session reuse, recovery-clear correctness, cleanup/resource leaks, presence races, `pymobiledevice3` API misuse, security regression and sensitive logging. Do not spend repeated reviews on formatting or mechanically proven changes.

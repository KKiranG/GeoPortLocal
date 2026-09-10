# GeoPortLocal agent instructions

## Mission

Modernize GeoPortLocal into a reliable, locally run iOS location-simulation and Australian fuel-price tool while preserving the existing user workflow where it is still useful.

The current `main` branch is the legacy baseline. Do not rewrite or overwrite legacy behavior casually. Work on the modernization branch and make changes in small, testable slices.

GeoPortLocal is the product name. Do not rename it to Fuel Next, GeoPort 5, or another product.

## Scope boundaries

In scope:
- current iOS device discovery, pairing, developer-service connectivity and location simulation;
- deterministic set / clear / disconnect behavior;
- Australian fuel-price viewing and map selection;
- local-only security, packaging, diagnostics and maintainability;
- macOS Apple Silicon first, then Windows; Linux is secondary unless a task explicitly targets it;
- current supported `pymobiledevice3` public Python APIs.

Out of scope unless the founder explicitly changes scope:
- route playback, walking simulation, GPX automation, joystick features, social/location-app features;
- account automation or multi-account tooling;
- bypassing third-party anti-abuse, geofence, device-integrity or location-manipulation controls;
- VPN/IP matching, fingerprint concealment, jailbreak/root hiding, A01/A09 evasion, or any code whose purpose is to make a third-party service accept manipulated location;
- unrelated redesigns.

GeoPortLocal may simulate a device location and display fuel-price data. It must not claim that a successful device simulation means any third-party app will accept that location.

## Context discipline

Do not read the whole repository by default. Start with the task and load only the relevant context.

- Current handoff: `docs/WORKLOG.md`
- Local/real-device procedure: `docs/LOCAL_BOOTSTRAP.md`
- Bounded Codex sessions: `docs/CODEX_HANDOFF.md`
- Product scope / sequencing: `docs/MASTER_PLAN.md`
- Runtime and module boundaries: `docs/ARCHITECTURE.md`
- Required regressions / acceptance cases: `docs/TEST_MATRIX.md`
- Evidence and external assumptions: `docs/RESEARCH_2026-09.md`
- Codex/Astra working method: `docs/AGENT_WORKFLOW.md`

For a narrow code change, inspect the target file, adjacent code, its tests, and the relevant section of one design document. Do not reopen all design documents every turn.

Use targeted search (`rg`, specific file reads, focused tests) rather than recursive dumps. Images and large legacy HTML templates are expensive context; inspect them only when the task concerns them.

## Engineering invariants

1. Never report `connected`, `ready`, `simulating`, `cleared`, or equivalent success before the underlying operation has completed successfully.
2. Never cache an incomplete or invalid device session. A session without a valid live service provider is not reusable.
3. One selected device has at most one active device session and one active location-simulation operation.
4. Disconnect, clear, cancellation and shutdown must be idempotent.
5. A device disconnect or transport failure invalidates the session immediately. Recovery creates a fresh session rather than reusing stale host/port state.
6. Device functionality must not depend on fuel-price, GitHub, IP-geolocation, map-tile or other unrelated network services.
7. The local control plane binds to loopback only. Do not expose Flask/FastAPI on `0.0.0.0` by default.
8. Browser-facing localhost requests must keep the local Host/origin boundary: reject non-local Host values and cross-site mutating API requests.
9. Do not load remote executable JavaScript into the localhost control origin. Optional external map content is image-only and must be constrained by CSP.
10. Do not disable TLS verification.
11. Normal logs must not dump full UDIDs, pair records, exact selected coordinates, credentials or other secrets.
12. Prefer `pymobiledevice3` documented/public library APIs. Do not import `pymobiledevice3.cli.*` internals into application code.
13. Prefer one coherent asyncio runtime. Do not introduce unmanaged background threads when the same behavior can be expressed without them.
14. Avoid dependency additions unless they remove more complexity than they add.

## Change method

Before editing, state the smallest behavior being changed and the acceptance condition. Preserve unrelated behavior.

For device-runtime changes:
- write or update a focused unit/contract test first where practical;
- implement against a project-owned adapter so `pymobiledevice3` specifics do not leak into web/UI code;
- test failure paths, not only the success path;
- run targeted tests first, then the full fast suite.

For browser/control-plane changes:
- keep executable assets local;
- preserve CSP, Host validation and cross-site mutation rejection unless a proven compatibility issue requires a reviewed replacement;
- never make device actions depend on map or fuel availability.

For legacy extraction/refactoring, do not mix large moves with behavior changes in the same commit when avoidable.

For external dependencies or iOS behavior, verify current upstream documentation/source before changing architectural assumptions. Record material changes in `docs/RESEARCH_2026-09.md` or a later dated research note.

## Dependency baseline

The modernization target is Python 3.14 on development machines unless a platform-specific blocker is demonstrated. `pymobiledevice3` must be pinned through the project lockfile, initially against the current audited version rather than floated. Packaging must also be pinned.

When upgrading `pymobiledevice3`, review its Python API/tunnel documentation and run the hardware smoke matrix before accepting the upgrade.

## Tests and completion

A change is not done because the UI looks correct. It is done when:
- targeted tests pass;
- the relevant regression case in `docs/TEST_MATRIX.md` is covered or explicitly marked hardware/local-only;
- errors propagate truthfully to the UI/API;
- no new orphan task/thread/process is introduced;
- localhost security invariants remain enforced;
- `git diff` contains only intentional changes;
- docs are updated if a contract or architectural decision changed.

Do not mark a committed test `PASS` until it has actually run successfully in the target locked environment. `TEST EXISTS` and `PASS` are different evidence states.

Do not create broad speculative tests or duplicate test files. Put tests in the nearest existing test module once the test layout exists.

## Agent behavior

Do the work, not a large preamble. Prefer one implementation path and finish it before proposing optional improvements.

Do not perform unrelated cleanup while touching a file. Do not convert working code to a different framework merely because it is newer.

When blocked by hardware, leave the repository in a testable state, add the exact local command and expected observation to the relevant test matrix, and report the blocker precisely.

Use normal Codex for deterministic mechanical work such as locking, linting and routine test fixes. Reserve GPT-6 Astra for difficult real-device/tunnel diagnosis or architecture-sensitive repairs where the additional reasoning is justified.

Use subagents only for genuinely separable research/review tasks. Do not spawn agents to reread the same files. The primary agent owns integration and final verification.

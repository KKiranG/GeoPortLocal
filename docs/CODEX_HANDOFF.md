# Codex / Astra handoff

Date: 2026-09-10  
Branch: `geoportlocal-modernization`

The hardware-independent implementation is in the branch. The next useful work is local verification against the user's actual Mac/iPhone, not another broad redesign.

Start with root `AGENTS.md`, `docs/WORKLOG.md`, this handoff and only the required section of `docs/LOCAL_BOOTSTRAP.md`. Legacy `src/main.py` and `src/templates/map*.html` are reference material only.

## Session 1 — environment and deterministic fast gate

This is mechanical verification. Do **not** spend an Astra turn on it by default. Use the normal Codex model available to the user.

Prompt:

```text
Work only in KKiranG/GeoPortLocal on branch geoportlocal-modernization.
Read AGENTS.md, docs/WORKLOG.md, and sections 2-4 of docs/LOCAL_BOOTSTRAP.md. Do not scan legacy src/main.py, legacy map templates, images, Git history or research docs unless a specific failure requires them.

Goal: establish the exact local Python 3.14/uv baseline without redesigning anything.

1. Confirm branch and clean working tree.
2. Run `uv lock`, then `uv sync --locked`.
3. Run `uv run ruff check .` and `uv run pytest`.
4. Fix only real source/test/packaging-metadata failures revealed by those commands.
5. Re-run the complete fast gate.
6. Inspect uv.lock for the expected direct pins, especially pymobiledevice3==11.12.1 and pyinstaller==6.22.2.
7. Commit uv.lock plus only necessary fixes in one focused commit.

Do not upgrade dependencies, add features, change architecture or use subagents for routine failures.
Return only commands/results, files changed and any remaining blocker.
```

Exit gate: locked sync + Ruff + full pytest are clean. If they are not, stay in this session until the smallest reproducible failure is fixed or precisely classified.

## Session 2 — source app and real iPhone

Start with the normal Codex model. Escalate the same concrete failure to Astra only if the evidence shows a difficult tunnel/DVT/lifecycle problem or an architecture-sensitive repair.

Prompt:

```text
Continue on geoportlocal-modernization. Read AGENTS.md, docs/WORKLOG.md, section 5 of docs/LOCAL_BOOTSTRAP.md and only the relevant hardware rows in docs/TEST_MATRIX.md.

Goal: qualify the current source app and pymobiledevice3 adapter on this Mac/iPhone without adding features.

Run `uv run geoportlocal --no-browser`, use the printed local URL, and walk the hardware sequence in order:
- no-phone launch;
- USB attach/discovery;
- connect;
- one location set with independent device-side verification;
- clear;
- 20 set/clear cycles;
- unplug while READY and reconnect;
- unplug while SIMULATING and reconnect;
- clean shutdown/relaunch.

For any failure:
1. reproduce once;
2. capture the smallest redacted evidence;
3. classify it to usbmux metadata, trust/developer mode, PreferredRsdTunnel, DVT/LocationSimulation, SessionManager/API/UI, or another precise layer;
4. fix only that layer;
5. add/update the smallest regression test when practical;
6. rerun `bash scripts/check.sh` after source changes.

Preserve the project-owned adapter boundary. Never treat a third-party application's acceptance/rejection as the GeoPortLocal success oracle.
Update only hardware rows actually observed. Do not mark unrun rows PASS.
```

Astra escalation prompt, only when needed:

```text
Use GPT-6 Astra for this already-reproduced GeoPortLocal integration failure only.
Read AGENTS.md, the redacted failure evidence, the target module/adjacent tests and the relevant architecture/test section. Do not reopen the full legacy repository.

Determine whether the audited pymobiledevice3/tunnel lifecycle assumption is wrong on this Mac/iPhone or whether the bug is in GeoPortLocal ownership/error handling. Produce the smallest evidence-backed fix, targeted regression test, full fast-gate result and remaining hardware observation. No unrelated refactor.
```

## Session 3 — fuel/offline qualification

Use the normal Codex model unless a live provider schema change is genuinely ambiguous.

Prompt:

```text
Read AGENTS.md, docs/WORKLOG.md and section 6 of docs/LOCAL_BOOTSTRAP.md.

Goal: qualify fuel and offline degradation without touching device architecture.

Verify live region/type/quote normalization, quote-to-coordinate selection without automatic device mutation, then disconnect Internet and prove local health/device controls remain independent. If Project Zero Three changed schema, inspect only the live response contract and fuel provider/tests, then make the narrowest normalization change.

Run `bash scripts/check.sh` after source changes and record the live-provider observation without claiming provider availability is an application invariant.
```

## Session 4 — packaged app

Run only after the source app passes the core hardware path. Use normal Codex first; escalate to Astra only for a non-obvious native/dynamic-import lifecycle failure.

Prompt:

```text
Read AGENTS.md, docs/WORKLOG.md, section 7 of docs/LOCAL_BOOTSTRAP.md, packaging/GeoPortLocal.spec and only the packaging-specific failure evidence.

Goal: produce and qualify dist/GeoPortLocal.app side-by-side with the existing GeoPort app.

Run `bash scripts/build_macos.sh`. Fix only reproducible PyInstaller/data-file/dynamic-import/macOS bundle issues. Keep app name GeoPortLocal and bundle id io.github.kkirang.geoportlocal. Do not overwrite, rename, kill or modify the existing GeoPort application.

Test packaged launch, actual dynamic loopback URL, device discover/connect/set/clear, shutdown and relaunch. Re-run the fast gate after source changes. Do not optimize bundle size until correctness is proven.
```

## Context and usage rules

- one concrete outcome per session;
- normal Codex for deterministic/mechanical work;
- Astra only for difficult integration or architecture-sensitive uncertainty;
- inspect target module + adjacent tests before broad search;
- use `rg` for symbols instead of recursive dumps;
- never preload both large legacy templates;
- do not preload all research/OzBargain material for coding work;
- no review swarm or duplicate agents;
- no strong-model review when a narrow test already mechanically proves a low-risk change;
- do not upgrade `pymobiledevice3`, Python or PyInstaller during qualification unless evidence specifically requires reevaluating that baseline.

## Intentional architecture — do not redesign without evidence

- Python 3.14 baseline;
- FastAPI/uvicorn loopback-only backend;
- local HTML/CSS/JavaScript UI;
- project-owned map logic with remote image tiles only;
- one SessionManager;
- current public `pymobiledevice3` APIs only;
- `PreferredRsdTunnel -> DvtProvider -> LocationSimulation` for modern iOS;
- iOS 17.4+ first;
- Project Zero Three behind a provider boundary;
- preferred 54321 with atomic alternate loopback-port reservation;
- legacy GeoPort remains installed as fallback;
- no third-party anti-abuse/geofence/device-integrity bypass work.

A failed real observation can justify changing one of these. Novelty or preference cannot.

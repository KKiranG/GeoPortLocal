# Codex / Astra handoff

Date: 2026-09-10  
Branch: `geoportlocal-modernization`

This file is the local-development handoff after the GitHub-only modernization work. It is intentionally shorter than the design documents.

## Current boundary

The hardware-independent architecture and implementation are in the branch. The next useful Codex work is **verification against the user's actual Mac/iPhone**, not another broad redesign.

Do not ask Codex to reread the entire legacy repository. Start with root `AGENTS.md`, this handoff, `docs/WORKLOG.md`, and only the section of `docs/LOCAL_BOOTSTRAP.md` required for the current task.

The old `src/main.py` and `src/templates/map*.html` are reference material only. Open a specific part of them only when a concrete compatibility question cannot be answered from the new implementation.

## Session 1 — environment and deterministic fast gate

Use one Astra turn for this entire package because it is tightly related and does not require the phone.

Suggested prompt:

```text
Work only in KKiranG/GeoPortLocal on branch geoportlocal-modernization.
Read AGENTS.md, docs/WORKLOG.md, and sections 2-4 of docs/LOCAL_BOOTSTRAP.md. Do not scan src/main.py, legacy map templates, images, Git history, or research docs unless a specific failure requires them.

Goal: establish the exact local Python 3.14/uv baseline without redesigning anything.

1. Confirm the branch and clean working tree.
2. Run `uv lock`, then `uv sync --locked`.
3. Run `uv run ruff check .` and `uv run pytest`.
4. Fix only real source/test/packaging-metadata failures revealed by those commands. Do not upgrade dependencies, add features, or change architecture.
5. Re-run the complete fast gate.
6. Inspect the generated uv.lock for the expected direct dependency pins, especially pymobiledevice3==11.12.1 and pyinstaller==6.22.2.
7. Commit uv.lock plus only necessary fixes in one focused commit.

Return: commands run, exact pass/fail counts, files changed, and any remaining blocker. Keep context narrow and do not use subagents unless one isolated dependency-resolution question genuinely requires it.
```

If this session passes, there should be no reason to run a broad repository review.

## Session 2 — real device qualification

Connect the actual iPhone only after Session 1 is clean.

Suggested prompt:

```text
Continue on geoportlocal-modernization. Read AGENTS.md, docs/WORKLOG.md, and section 5 of docs/LOCAL_BOOTSTRAP.md plus the hardware rows in docs/TEST_MATRIX.md. Do not inspect legacy UI/source unless a failed observation specifically requires comparison.

Goal: qualify the current pymobiledevice3 adapter on this Mac/iPhone without adding features.

Run `uv run geoportlocal --no-browser`, use the printed local URL, and walk the hardware matrix in order: no-phone launch, USB discovery, connect, one set, independent on-device verification, clear, 20 set/clear cycles, unplug while READY, reconnect, unplug while SIMULATING, reconnect, clean shutdown.

For each failure: reproduce once, capture the smallest redacted log/evidence, identify which layer failed (usbmux metadata, trust/developer mode, PreferredRsdTunnel, DVT, LocationSimulation, SessionManager/API/UI), and fix only that layer. Preserve the project-owned adapter boundary. Never report a third-party application's acceptance/rejection as proof of GeoPortLocal success/failure.

Update only the actual hardware rows in docs/TEST_MATRIX.md with observed results. Do not mark unrun rows PASS.
```

The primary value of Astra here is diagnosis of real integration evidence, not generating more abstractions.

## Session 3 — packaged app qualification

Run only after the source app passes the core hardware path.

Suggested prompt:

```text
Read AGENTS.md, docs/WORKLOG.md, section 7 of docs/LOCAL_BOOTSTRAP.md, packaging/GeoPortLocal.spec, and any packaging-specific failing log. Do not reopen the general architecture unless the package failure proves it is wrong.

Goal: produce and qualify dist/GeoPortLocal.app side-by-side with the existing GeoPort app.

Run `bash scripts/build_macos.sh`. Fix only reproducible PyInstaller/data-file/dynamic-import/macOS bundle issues. Keep app name GeoPortLocal and bundle id io.github.kkirang.geoportlocal. Do not overwrite, rename, kill, or modify the existing GeoPort application. Re-run the fast gate after source changes and test the packaged app separately for launch, actual dynamic port URL, device discover/connect/set/clear, shutdown and relaunch.

Do not optimize bundle size until packaged correctness is proven.
```

## Context budget rules

For Astra/Codex turns:

- one outcome per turn;
- inspect target module + adjacent tests before any broad search;
- use `rg` for symbols instead of recursive file dumps;
- never preload both 100 KB legacy templates;
- do not preload all research/OzBargain material for coding work;
- do not ask multiple agents to review the same change;
- use the fast fake-adapter tests for ordinary edits and reserve the iPhone for dependency-boundary changes;
- do not spend a strong-model review on a change that is already mechanically proven by a narrow test unless the risk is architectural.

## What not to redesign

These choices are intentional unless hardware evidence disproves them:

- Python 3.14 development baseline;
- FastAPI/uvicorn local backend;
- plain HTML/CSS/JavaScript UI;
- one SessionManager;
- current public pymobiledevice3 API only;
- `PreferredRsdTunnel -> DvtProvider -> LocationSimulation` for the modern iOS path;
- iOS 17.4+ first;
- Project Zero Three behind a provider boundary;
- loopback-only server;
- automatic alternate loopback port when the preferred default is occupied;
- existing GeoPort remains installed as fallback;
- no third-party anti-abuse/geofence/device-integrity bypass work.

A failed real observation can justify changing one of these. Preference or novelty cannot.

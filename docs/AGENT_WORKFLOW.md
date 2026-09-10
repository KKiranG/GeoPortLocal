# Astra / Codex workflow for GeoPortLocal

Date: 2026-09-10

## 1. Objective

Use Codex with GPT-6 Astra for high-quality implementation without making every turn reload the legacy source, research history and every design document.

This repository is deliberately structured so durable detail lives in docs while `AGENTS.md` stays short enough to be cheap and unambiguous.

## 2. Current Astra facts

As of 2026-09-10:

- GPT-6 Astra is the current frontier model being rolled into Codex.
- OpenAI says Astra requires Codex CLI **0.153.0 or newer**.
- Astra is more sensitive than earlier models to instructions found in `AGENTS.md`, skills and other accessible instruction files.
- Codex allowance consumption varies with task size, codebase size, context and run duration; larger long-running tasks cost materially more allowance.

Operational consequence: do not use a huge universal prompt or huge `AGENTS.md`. Give Astra one bounded outcome and the minimum durable context required for that outcome.

Official references:

- https://openai.com/index/gpt-6-astra/
- https://developers.openai.com/api/docs/guides/latest-model
- https://help.openai.com/en/articles/11369540-codex-and-chatgpt-plan-usage-limits
- https://developers.openai.com/

## 3. Before the first local session

After pulling the branch locally:

```bash
git switch geoportlocal-modernization
git pull --ff-only
codex --version
```

If Codex is older than 0.153.0, update Codex through the same installation method already used on the Mac, then verify the version again. Do not change the user's broader Codex multi-account setup as part of this repository task.

Start Codex from the repository root for project-level work so the root `AGENTS.md` is loaded.

Do not create a committed `AGENTS.override.md`. Overrides are for temporary local experiments and can silently replace the normal instruction file at that directory level.

## 4. Context-loading rule

For each work package, load:

1. root `AGENTS.md` automatically;
2. the relevant section of `docs/MASTER_PLAN.md`;
3. one relevant architecture/test document section;
4. the target source files and adjacent tests.

Do **not** begin a normal coding turn by reading:

- every Markdown file;
- all of `src/main.py` plus both 100 KB templates;
- all Git history;
- all upstream issues;
- all OzBargain research.

The research has already been distilled into `docs/RESEARCH_2026-09.md`. Re-open external sources only when the implementation decision depends on something that may have changed.

## 5. One-turn work-package size

A normal Astra turn should implement one coherent vertical slice that can be validated before the turn ends.

Good:

```text
Define DeviceState + domain errors and add their unit tests.
```

Good:

```text
Implement SessionManager.connect() against FakeDeviceAdapter and cover S01/S02/S06/S08.
```

Good:

```text
Implement the pymobiledevice3 iOS 17.4+ connect/set/clear adapter only. Do not touch the UI.
```

Bad:

```text
Modernize the whole GeoPort repository, update the UI, fix all issues and package it.
```

The bad prompt forces broad exploration, increases allowance use, and makes review difficult.

## 6. Standard implementation prompt

Use this structure for Codex turns:

```text
Implement work package <name> on branch geoportlocal-modernization.

Read root AGENTS.md, then only the relevant sections of:
- docs/MASTER_PLAN.md: <phase/section>
- docs/ARCHITECTURE.md: <section>
- docs/TEST_MATRIX.md: <test IDs>

Inspect the target files and adjacent tests before editing. Do not read unrelated images or legacy templates unless required.

Goal:
<one concrete behavior>

Acceptance:
- <specific test/observable result>
- <specific test/observable result>
- no unrelated changes

Run targeted tests first, then the fast full suite if targeted tests pass. Review git diff before finishing. Report changed files, tests run, and any hardware-only follow-up. Do not create extra features or compatibility paths not required by this work package.
```

This template is intentionally short because durable project rules are already in the repository.

## 7. Exploration budget

For a narrow task, Astra should normally inspect no more than:

- 1-3 design/test document sections;
- 2-6 source files;
- 1-3 test files;
- targeted upstream code/docs only if needed.

This is a guideline, not a hard limit. If the bug crosses boundaries, inspect what is necessary, but explain why before broadening scope.

Use targeted commands:

```bash
rg "symbol_or_error" src tests docs
sed -n '120,220p' path/to/file.py
git diff -- path/to/file.py
git diff --stat
pytest path/to/test_file.py -q
```

Avoid giant `cat`/recursive dumps.

## 8. Subagents

Astra can handle this repository without a swarm.

Default: primary Astra agent only.

Use at most two subagents when tasks are truly independent, for example:

- one inspects current `pymobiledevice3` API details;
- one checks existing regression tests for an unrelated boundary.

Do not ask multiple agents to review the same files. Do not spawn a separate agent for formatting, README edits or running the same tests.

The primary agent owns integration, test execution and final diff review.

## 9. When Astra is worth spending

Use Astra for:

- architecture-sensitive changes;
- async lifecycle/session ownership;
- real `pymobiledevice3` integration;
- difficult connection/reconnect bugs;
- migration of legacy behavior where source intent is unclear;
- final review before hardware qualification.

Do not spend a fresh high-context Astra turn merely to:

- rename a variable;
- format a file;
- update a known test expectation;
- inspect a single log line that can be handled in the current session.

Keep the same Codex session while working within one work package and its immediate fixes. Start a clean session when switching subsystem or when accumulated context has become mostly irrelevant.

## 10. Worktree/branch discipline

Primary development branch:

```text
geoportlocal-modernization
```

For risky parallel implementation, create short-lived branches from it, e.g.:

```text
modernize/device-session
modernize/fuel-provider
modernize/ui-shell
```

Do not ask two agents to modify the same files concurrently.

Prefer small commits with one purpose:

```text
build: add reproducible Python project
refactor: add device domain model
feat: add async pymobiledevice adapter
feat: add deterministic session manager
feat: isolate fuel provider
```

Avoid commits combining mass formatting, file moves and behavior changes.

## 11. Testing cadence

Every implementation turn follows:

```text
inspect -> targeted test -> implement -> targeted test -> relevant full tests -> diff review
```

Do not run hardware tests for code that fails fake-adapter/unit tests.

Hardware testing is reserved for boundaries automation cannot prove:

- actual USB discovery;
- real pairing/trust state;
- current iOS developer-service connection;
- real location set/clear;
- unplug/reconnect behaviour;
- packaging on the actual Mac.

Record results in `docs/TEST_MATRIX.md` so the next agent does not need the previous chat transcript.

## 12. Session handoff

At the end of a meaningful work package, update `docs/WORKLOG.md` with no more than:

- current phase/work package;
- last completed commit;
- tests passing;
- exact next task;
- blockers requiring hardware/user action.

Do not turn WORKLOG into a diary. Its job is to let a fresh Astra session resume in under a minute without rereading the whole repository or chat history.

## 13. Review prompt

After a substantial device-runtime work package, use one focused independent review rather than repeated generic reviews:

```text
Review only the current branch diff for correctness against:
- AGENTS.md engineering invariants
- docs/ARCHITECTURE.md relevant contract
- docs/TEST_MATRIX.md relevant IDs

Prioritize false success, stale-session reuse, async lifecycle leaks, missing cleanup and incorrect pymobiledevice3 API use. Do not propose stylistic rewrites or unrelated features. Return concrete findings with file/line references. If no material issue exists, say so.
```

Fix material findings, rerun tests, then continue. Five redundant reviews are not the plan.

## 14. Rules for updating external assumptions

Search current upstream sources when changing any of these:

- `pymobiledevice3` major/minor version;
- iOS transport strategy;
- Python/PyInstaller baseline;
- Codex/Astra configuration assumptions;
- Project Zero Three response contract.

Do not web-search OzBargain during ordinary device-runtime coding. Community evidence is relevant to product symptoms, not to every code edit.

If new external evidence changes an architectural assumption, append a dated research note and update the affected plan/architecture section in the same change.

## 15. Completion report format

Astra should finish an implementation turn with only useful evidence:

```text
Changed:
- ...

Verified:
- pytest ... -> N passed
- ...

Remaining:
- Hxx hardware check required: <exact action>
```

No generic essay, no repeated project summary, and no re-pasting the full plan.
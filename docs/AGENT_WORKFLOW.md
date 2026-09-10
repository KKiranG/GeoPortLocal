# Codex / Astra workflow for GeoPortLocal

Date: 2026-09-10

## 1. Current objective

The broad modernization implementation is already on `geoportlocal-modernization`. Agent work should now prove it locally, diagnose only observed failures, and avoid reopening architecture that has not been falsified by evidence.

The repository keeps durable rules in `AGENTS.md` and focused docs so Codex does not need to reload the legacy monolith or this chat history.

## 2. Current model allocation

As of 2026-09-10, GPT-6 Astra is rolling out in Codex and requires Codex CLI 0.153.0 or newer. OpenAI also notes that Astra can consume Codex allowance faster than GPT-5.6 Sol depending on task size, context and reasoning settings.

Operational rule:

- deterministic mechanical work: normal Codex model;
- difficult real iPhone/tunnel diagnosis or architecture-sensitive repair: Astra;
- do not spend Astra on `uv lock`, formatting, routine Ruff fixes, obvious test expectation changes or README maintenance.

Official references:

- https://openai.com/index/gpt-6-astra/
- https://help.openai.com/en/articles/20001275

## 3. Entry point for the next local session

After syncing locally:

```bash
git switch geoportlocal-modernization
git pull --ff-only
git status --short
codex --version
```

Then read, in order:

1. root `AGENTS.md`;
2. `docs/WORKLOG.md`;
3. the relevant session in `docs/CODEX_HANDOFF.md`;
4. only the required section of `docs/LOCAL_BOOTSTRAP.md`.

Do not start by rereading `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, all research, legacy `src/main.py`, both legacy map templates and Git history. Open those only when a concrete failure needs them.

Do not create a committed `AGENTS.override.md`.

## 4. Context-loading discipline

For an observed failure, inspect the smallest responsible layer first:

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

Normal context budget for a narrow fix:

- `AGENTS.md` plus one handoff/test section;
- 1-4 target source files;
- adjacent tests;
- one upstream source only if the dependency contract itself is uncertain.

Use targeted commands such as:

```bash
rg "symbol_or_error" src tests docs
sed -n '120,220p' path/to/file.py
git diff -- path/to/file.py
uv run pytest tests/test_target.py -q
```

Avoid recursive dumps, loading all images, or opening both large legacy HTML templates without a specific reason.

## 5. Standard repair prompt

For a real failure, use a bounded prompt:

```text
Work only in KKiranG/GeoPortLocal on branch geoportlocal-modernization.
Read AGENTS.md, docs/WORKLOG.md and the relevant section of docs/LOCAL_BOOTSTRAP.md or docs/TEST_MATRIX.md.

Observed failure:
<exact redacted evidence>

Goal:
identify the smallest failing layer and fix only that failure.

Requirements:
- inspect target code and adjacent tests before editing;
- preserve current architecture unless the evidence proves a contract wrong;
- add/update the smallest regression test that demonstrates the failure when practical;
- run the targeted test first, then `bash scripts/check.sh` after the fix;
- review `git diff` before finishing;
- do not upgrade dependencies, restore legacy features, or perform unrelated cleanup.

Return only: root cause, files changed, tests run/results, and remaining hardware observation.
```

## 6. When to use Astra

Astra is justified when the remaining uncertainty is genuinely integration-heavy, for example:

- current `pymobiledevice3` API behavior differs from the audited assumption;
- `PreferredRsdTunnel` fails differently on the actual macOS/iOS combination;
- DVT/LocationSimulation lifecycle has a non-obvious async cleanup bug;
- unplug/reconnect exposes stale resource ownership not reproduced by fakes;
- a packaged-app failure involves dynamic imports/native resources and requires cross-layer reasoning;
- a proposed fix would alter a documented architectural invariant.

Even then, use one primary Astra agent. Do not create a review swarm.

## 7. Subagents

Default: none.

Use at most two only when work is truly separable, such as one agent checking a current upstream dependency contract while the primary agent diagnoses local evidence. Do not ask multiple agents to inspect the same diff or rerun the same tests.

The primary agent owns integration, verification and final diff review.

## 8. Testing cadence

For code changes:

```text
reproduce
-> classify layer
-> targeted test
-> minimal fix
-> targeted test
-> bash scripts/check.sh
-> diff review
```

Do not run hardware tests for code that fails the fast suite.

Hardware evidence is required for:

- real USB discovery and metadata;
- trust/pairing state;
- Developer Mode behavior;
- actual `PreferredRsdTunnel` connection;
- real location set/clear;
- unplug/reconnect;
- live provider compatibility;
- frozen macOS application behavior.

Record only observations actually made in `docs/TEST_MATRIX.md`.

## 9. Branch and commit discipline

Primary branch:

```text
geoportlocal-modernization
```

Do not modify `main` during qualification.

Prefer one focused commit per proven fix. Do not combine mass formatting, broad file movement and behavior changes. Do not create short-lived branches unless a risky experiment genuinely benefits from isolation.

## 10. Review policy

One focused review is enough after a material runtime repair.

Review against:

- `AGENTS.md` invariants;
- the relevant `docs/ARCHITECTURE.md` contract;
- the affected `docs/TEST_MATRIX.md` IDs.

Prioritize:

- false success;
- stale-session reuse;
- async/resource leaks;
- missing cleanup;
- incorrect dependency use;
- unintended exposure beyond loopback;
- identifier/secret leakage.

Ignore stylistic churn unless it creates correctness risk.

## 11. External research rule

Recheck current upstream sources only when changing an assumption that may have moved:

- `pymobiledevice3` version/API;
- iOS transport strategy;
- Python/PyInstaller baseline;
- Codex/Astra requirements;
- Project Zero Three response contract.

Do not repeatedly research OzBargain or third-party acceptance behavior during ordinary coding. That is not the correctness oracle for GeoPortLocal.

If new evidence changes an architectural assumption, update the dated research note and affected contract in the same change.

## 12. Handoff rule

At the end of a meaningful local package, keep `docs/WORKLOG.md` short and current:

- current phase;
- exact verification completed;
- last focused commit;
- next action;
- genuine blocker.

Do not turn it into a diary.

## 13. Completion report

Codex should finish with evidence, not a project essay:

```text
Changed:
- ...

Verified:
- command -> result
- command -> result

Remaining:
- Hxx: exact hardware observation still required
```

If no material change was needed, say so and do not manufacture cleanup work.

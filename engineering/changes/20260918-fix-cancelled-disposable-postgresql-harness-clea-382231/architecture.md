# Architecture — Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The runner creates a nonce-labelled container but relies on an anonymous image volume. Normal docker rm -f leaves that volume behind. Startup does not reclaim interrupted runs. Python's default SIGTERM action bypasses finally, and the verifier's generic subprocess.run path does not own or stop the child process group. Inner TimeoutExpired becomes a traceback/exit 1; outer timeout becomes generic exit 124.

## Proposed behavior

Give each invocation a unique nonce, explicitly labelled disposable volume, and exact container-to-volume mount. Reclaim only resources older than a conservative documented TTL after re-inspecting full ID/name/image/label/mount/volume driver and nonce; exclude current nonce and preserve ambiguous resources. Log each reclaimed identity and reason into check output. On cancellation, stop and reap active descendants within a grace deadline, then let the harness unwind and remove only its exact bound resources. On timeout, emit phase, elapsed time, and budget while preserving a failing check result.

The per-run recovery candidate limit is global across resource categories: a stale container and its bound volume form one candidate bundle; detached stale volumes consume the same remaining allowance. The verifier's TERM grace exceeds the harness's bounded unwind path, with TERM escalation and final reap still inside the existing 600-second cap.

## Components and boundaries

- factory/tests/run_disposable_exit.py: resource ownership, startup reaper, phase budgets, signal unwinding, diagnostics.
- .grok-stack/adaptive_grok/verification.py / .grok-stack/adaptive_grok/util.py: ensure the exit check is cancellable, generic verifier timeouts terminate their isolated process groups, and timeout details are not flattened.
- factory/tests/test_migrations.py: identity/reclamation and timeout coverage; subprocess-level signal regression with isolated fake commands.

## Data flow

Create nonce and labelled volume → inspect and bind exact container+mount → run bounded setup/tests/restart phases → on success/failure/cancellation stop and reap owned process groups → validate exact ownership (retrying name-to-ID lookup only within its bounded deadline) → remove container and volume → report reclaimed resources and outcome. A later run reaps only verified resources past TTL. Generic verifier commands use isolated POSIX sessions and bounded TERM→KILL cleanup on timeout. Reaper listings cap both returned bytes and scanned rows, and report backlog.

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- No cron or global prune. The harness is the sole cleanup owner.
- Preserve fail-closed gate status on timeout/cancellation; details distinguish inconclusive outcomes from assertion failures.
- TTL must exceed maximum bounded runner duration plus cleanup margin; choose it only after phase budget is bounded below the verifier's 600-second limit.

## Risks and mitigations

- Concurrent run deletion: TTL above maximum supported runtime, current nonce exclusion, and repeated full binding checks.
- Partial creation leaks: track the volume immediately and clean it even if container creation fails; startup recovery handles volume-only leftovers.
- Signal race with test descendants: stop/wait for the owned process group before Docker cleanup.
- Ambiguous Docker metadata: preserve resources and fail with an actionable identity-bound diagnostic.

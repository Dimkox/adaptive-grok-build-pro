# Architecture analysis — provider-neutral autonomous factory

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Role: read-only `architect`

## Verdict

The approved direction is coherent with the four-plane roadmap if the factory is treated as a new, untrusted execution system beside—never inside—the existing Trust CI authority. The core should own durable state, authorization, leases, budgets, workspaces, and protocol validation; provider adapters should be replaceable subprocess translators with no authority to change policy or task state directly.

The design must stop at the `scope_and_design_approval` gate. No M4 factory runtime is justified until the existing M1 typed-spec milestone is complete and M2/M3 publish stable machine contracts.

## Source facts

- `main`/current branch already contains the first M1 schema, parser, CLI, and tests (`48cb973`), but the milestone is not complete: the active package's `change-spec.yaml` still contains placeholders/`UNKNOWN`, its collections are empty, the external holdout validator is absent, and Trust CI attestation/criterion coverage integration is not evidenced.
- M2 architecture model/rules and M3 governance/debt trees do not exist. `factory/` does not exist. This is the correct pre-M4 state.
- M0 trust authority is already a separate PostgreSQL-backed exact-SHA system. `trust_ci.*` must not be reused as the factory queue, and factory processes must never receive its App key, attestation key, human trust store, policy, or holdout mutation capability.
- The current product contract already establishes one write owner, PR-only delivery, no GitHub Actions, local evidence as non-authoritative, and human ownership of merge/release/production promotion.

## Component and trust boundaries

| Boundary | Owns | Must not own |
| --- | --- | --- |
| Intent plane (M1/M2/M3) | Typed change spec, architecture rules/model, reviewed governance rules; immutable digests consumed by tasks | Runtime leases, provider credentials, task-state mutation |
| Factory API/supervisor (M4) | Intake validation, task state machine, scheduling, WIP limits, kill switches, reconciliation, policy-selected provider/role | Repository execution, provider-native parsing, Trust CI verdicts, autonomous external writes |
| PostgreSQL `factory.*` (M4) | Tasks, runs, lease generations, state transitions, notes, artifacts metadata, usage/cost ledger, worker heartbeats, idempotency keys | Trust CI jobs/approvals/attestations and secret bodies |
| Workspace manager/tool broker (M5) | Exact-SHA checkout/worktree lifecycle, path authorization, read/write mounts, command execution, sanitized environment, artifact collection | Provider selection, acceptance decisions, external credentials |
| Provider adapter (M5) | Translate one canonical invocation to provider CLI/API and normalize its stream to the canonical protocol | Scheduler/database access, policy decisions, direct state transitions, fallback selection, external-write credentials |
| Note broker (M5) | Append-only, sequenced, bounded, provenance-tagged findings and evidence references | Instructions, role/tool/budget changes, mutable shared memory, chain-of-thought |
| Semantic/review plane (M6) | Independent structured findings and `pass/repair/needs_human` recommendation against an immutable SHA | Workspace writes, implementer context/chain-of-thought, Trust CI publication |
| Trust CI | Independent exact-SHA verification and App-owned policy-epoch Check Run | Product implementation and factory task orchestration |

Provider, repository, prompt, notes, stdout/stderr, and model results are untrusted inputs. Only the control plane may validate them into durable facts. An adapter terminal result is a proposal; a transaction in the control plane decides the next state.

## Canonical adapter protocol

Keep provider-native formats behind adapters. `codex exec --json` is the first native integration, not the factory protocol itself; the Grok compatibility adapter has the same boundary. Future adapters implement a versioned process contract:

```text
fixed executable from operator configuration
stdin: exactly one canonical JSON invocation
stdout: bounded JSONL canonical events
stderr: bounded diagnostic channel, never protocol
exit: exactly one terminal event plus an allowed exit code
```

The invocation requires an exact protocol/schema version, `task_id`, `run_id`, role, provider/adapter/model identity, immutable packet/spec/architecture digests, exact base/head SHA when present, authorized paths/tools/network, acceptance IDs, and hard runtime/token/cost limits. It must not contain database credentials, Trust CI material, or external-write authority.

The first JSONL record is a capability/identity handshake. Subsequent allowlisted event types should be limited to lifecycle, bounded note/finding, artifact reference, usage, and terminal result/error. Every record carries protocol version, run identity, monotonically checked sequence, and type; the broker adds trusted receive time and durable sequence. Malformed JSON, oversized lines/streams, duplicate or missing terminal records, identity mismatch, unsupported protocol version, undeclared capability, or non-monotonic sequence fail closed.

Protocol version and adapter/provider/model versions are separate fields. Initial compatibility should require an exact supported protocol major/schema; migration uses explicit conformance fixtures and dual-version readers, never permissive guessing. Provider selection is persisted before dispatch. An unavailable/incompatible provider yields a typed failure or `needs_human`; there is no silent fallback. A Grok adapter that cannot prove required usage, isolation, or structured-output capabilities is ineligible for that role rather than silently downgraded.

Do not persist raw provider JSONL, raw prompts, private reasoning events, or unrestricted stderr. Normalize only concise conclusions, evidence references, structured findings, artifact digests, usage, and terminal status. Unknown or reasoning/scratchpad event types are dropped from evidence and cause a protocol-policy event as configured; no chain-of-thought becomes task memory.

## Durable control-plane invariants

- PostgreSQL is the operational source of truth. Filesystem artifacts are content-addressed and referenced by digest; Markdown is explanatory only.
- State transitions, notes, usage, and audit events are append-only. Mutable task projections are derived transactionally from those events; note insertion cannot update task policy or state.
- Lease claims use `FOR UPDATE SKIP LOCKED`, expiry, heartbeat, and a monotonically increasing fencing token. Every write/result commit checks the current token so an expired worker cannot publish late output.
- Idempotency covers intake, dispatch/run creation, note ingestion, artifact registration, and terminal-result application.
- Hard scheduler limits are global readers `<=20`, readers per repository `<=10`, and application writers `=1`. The writer limit is a PostgreSQL-enforced singleton lease/fence, not a systemd process-count convention.
- Infrastructure retries are at most two retries after the initial attempt; semantic repair cycles are separately capped at three. Retry class must be typed so deterministic/provider/policy failures cannot be mislabeled as infrastructure failures.
- Task wall time is at most four hours across execution and repair activity, and task provider cost is at most USD 25. Reservations occur before provider calls; usage is reconciled per event; missing trustworthy usage/cost telemetry blocks further calls. Deadline or budget exhaustion cancels execution and ends in a durable terminal/escalation state.
- Kill switches and WIP/budget exhaustion stop new dispatch without deleting evidence. Recovery after restart is reconciliation from PostgreSQL, not reconstruction from process memory.

## systemd and workspace model

Use fixed, reviewed systemd units for one supervisor and bounded reader/writer worker pools. Task content must never generate unit names, unit files, command lines, environment paths, users, or capability settings. systemd supplies process liveness and hardening; PostgreSQL supplies ownership and correctness. Restarting a unit must be safe because leases, fences, attempts, and budgets survive it.

Each run receives an exact-SHA, task-scoped worktree managed by the workspace manager. Readers receive an OS-level read-only view and can append only through the note broker. The single writer receives only its leased application workspace and allowed paths. Provider processes have no direct access to another task's workspace or broker/database credentials.

A Git worktree is not a security boundary: its `.git` indirection normally reaches the repository's shared common object/ref store. The design therefore must put the common Git directory behind the trusted workspace manager, deny agent subprocess access to it, and broker required Git operations; otherwise a nominally read-only worker could mutate shared refs or other worktrees. Namespace/mount isolation and adversarial cross-task tests are M5 acceptance requirements, not optional hardening.

Provider authentication also cannot be placed in an inherited environment. Credentials must terminate at a provider-control boundary that repository tool subprocesses cannot read (separate identity/namespace or a brokered channel), while repo commands run through a sanitized tool broker. The Codex adapter is not compliant until an adversarial subprocess proves it cannot enumerate or read provider, factory, Trust CI, or external credentials.

## Sequencing gates

1. Finish M1: make the active typed package complete/schema-valid, close criterion/evidence traceability and stale-digest/Trust CI holdout gaps.
2. Complete M2 and M3 contracts: executable component/trust/data-flow rules plus reviewed governance/debt lifecycle. M4 consumes their versioned digests and may not invent substitutes.
3. M4 introduces only the durable PostgreSQL control plane, leases, state/audit model, limits, and kill/reconciliation behavior.
4. M5 adds the versioned adapter protocol, Codex first adapter, Grok compatibility adapter, fixed systemd services, isolated worktrees/tool broker, note broker, and credential/network isolation.
5. M6 adds independent semantic findings/adjudication and at most three repairs returned to the same writer.
6. M7–M9 remain unavailable until their preceding exit evidence exists and a new scope/design decision authorizes them.

This is dependency sequencing, not an implementation plan: no later milestone interface may be used to declare an earlier milestone complete.

## Contradictions and required rulings

1. **M1 status wording conflicts.** The M0 spec says M1 is already on `main`, while the roadmap's M1 exit criteria and the current placeholder active spec are not satisfied. Treat the merged code as an M1 foundation, not milestone completion.
2. **Roadmap M7 conflicts with no autonomous external writes.** Its automated push/PR flow, M8 auto-merge, and M9 delivery cannot be active under the approved invariant. Through M6, the factory may produce a local branch/commit/evidence bundle and stop at `needs_human`/`ready_for_human`. Any later external write needs a separately approved capability and exact human/delegated gate; adapters never receive it.
3. **Roadmap M4 state names are premature.** `pr_open`, `merged`, and external source intake can exist only as reserved states/contracts while external writes are disabled. They must not imply capability in M4.
4. **Native provider JSON is not canonical evidence.** Persisting Codex's raw `--json` stream would couple the core to Codex and risks storing private reasoning/secrets. Only a validated, redacted canonical JSONL projection crosses the adapter boundary.
5. **Worktree isolation can be overstated.** Separate directories do not isolate the shared Git common directory. M5 must enforce OS/broker isolation before claiming cross-task or read-only safety.
6. **`readers<=20` and `per-repo<=10` are ceilings, not staffing targets.** They do not change the route-selected wave or justify idle agents. The application writer remains one globally unless a future approved specification explicitly scopes a different invariant.

## Design gate recommendation

Approve the provider-neutral boundaries and protocol shape above, with the six rulings incorporated into the written design and durable package. Do not begin M4/M5 implementation, create external-write credentials, install systemd units, or claim autonomous execution until M1, then M2/M3, have their own evidence and the user clears the current design gate.

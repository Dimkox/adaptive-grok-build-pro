# M5 Isolated Provider Execution — Design

## Status and authority

This is the approved implementation design for route `37b05f579320`, branch `milestone/m5-isolated-execution-provisional-m4`, and change [`20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f`](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/brief.md). M5 Tasks 1-6 originate at exact source head `141e51e75b2bb337fa3bb1544639c6c46c287309` and are locally normal-restacked on final exact M4 predecessor `571cad7877431ac5ab5779b53fe9f7effd6859ce` (tree `9d29f25d3af4fc9f97bbb8b3d4970906b69338fd`). This is provisional source integration, not M4/M5 acceptance or delivery; M5 requires fresh exact-head evidence.

The calendar target is `2026-09-08 00:00 UTC+3`. M5 and M6 may develop in parallel on isolated branches, but external integration is dependency ordered: accepted M4, then M5, then M6. This document grants no push, PR, merge, deployment, systemd activation, live provider call, credential access, or Trust CI/human-key operation.

Current M5 navigation: [root current state](../../../README.md) ↔ [factory roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ this design ↔ [implementation plan](../plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [change package](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/brief.md) ↔ [release](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/release.md) / [rollback](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/rollback.md) / [evidence](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/evidence/README.md).

## Factual M4 seam

M4 persists immutable accepted intent and exposes `/v1/claims`. A legacy claim allocates a run/fence/capacity slot and returns `packet_digest`, but the stored task `packet_digest` is exactly `intent_digest`. M4 has no provider, adapter, model, capability profile, stage, note, artifact, run manifest, or workspace identity. M5 must add an explicit execution path; changing the old field's meaning would silently corrupt replay, fencing, and audit compatibility.

The preserved legacy path is:

```text
accepted_intent.intent_digest
  = task.packet_digest
  = legacy /v1/claims LeaseGrant.packet_digest
```

The new execution path is:

```text
M4 task + live run/owner/fence/allocation + remaining deadline/budget
  + trusted ProviderProfileV1 + CapabilityPolicyV1 + ExecutionPlanV1
  -> canonical TaskPacketV1 bytes and new packet_digest
  -> immutable RunManifestV1
  -> /v1/execution/claims result
```

The old and new digests are separate domains and need not match.

## Outcomes and non-goals

M5 source provides deterministic contracts, parsers, fixture adapters, brokers, persistence/API surfaces, fake-runtime adversarial tests, recovery, metrics, static systemd topology, architecture/installer/doc parity, and an explicit host capability report. It makes provider-native behavior replaceable without making provider output authoritative.

M5 does not perform a provider call, network operation, repository subprocess, real workspace mutation, Git write, external action, systemd installation/activation, migration of any existing database, or production operation. M6 semantic judgment and repair remain outside M5.

## Immutable contracts

All contracts are closed, versioned, immutable nested Python value objects with canonical JSON Schemas. Strings are NFC UTF-8 Unicode scalar values; identifiers, digests, list order, list uniqueness, counts, depth, byte size, time, tokens, events, outputs, artifacts, notes, and cost are bounded.

`AuthorityBindingV1` binds repository, route, change, exact base/head SHA, spec, architecture, governance, policy, prompt-template, role-definition, tool-policy, and output-schema digests.

`ProviderProfileV1` binds provider, adapter ID/version/digest, native runtime version/digest, model ID, declared capabilities, and eligibility. Eligibility is an explicit conformance result. It is never inferred from an executable name or used to select a fallback.

`CapabilityPolicyV1` binds role, allowed repository paths, broker operations, tool names, network destinations, artifact classes, environment names, and denial defaults. Network destinations are empty for repository tools in this slice.

`ExecutionPlanV1` is an ordered tuple of stages from the closed set `prepare`, `invoke`, `collect`, `finalize`. Each stage has an owner and hard deadline/budget subset. Provider output cannot add, remove, reorder, or choose a stage.

`TaskPacketV1` binds task/run/repository identities, M4 run owner/fence/role, every authority/profile/policy/plan value, acceptance IDs, exact workspace handle, and limits. Its canonical bytes produce `packet_digest` in the `adaptive-factory.task-packet/v1` domain.

`RunManifestV1` binds packet digest, workspace handle, provider/profile identity, start deadline, initial stage and a manifest digest. It is immutable; stage changes append separate records.

## Provider-neutral protocol

The invocation input is exactly one bounded canonical JSON object. Output is a bounded UTF-8 JSONL stream. Protocol records are closed and carry protocol version, task/run/packet identity, producer sequence, event type, and a closed payload.

Allowlisted canonical events are `adapter.ready`, `run.started`, `stage.reported`, `note.proposed`, `artifact.proposed`, `usage.reported`, and exactly one of `run.completed`, `run.failed`, `run.needs_human`. `finding.proposed` is reserved as a named M6 bridge input and is not accepted or invented by M5.

The incremental parser enforces per-line, aggregate-byte, event-count, nesting, node, string, sequence and terminal bounds before retaining data. It rejects invalid UTF-8/JSON, non-finite numbers, duplicate keys, unknown required types, task/run/packet mismatch, duplicate or non-monotonic sequence, output after terminal, missing/duplicate terminal, and undeclared capabilities.

Keys or event kinds suggesting reasoning, scratchpad, chain-of-thought, hidden analysis, raw prompt, native stream, unrestricted stdout, or unrestricted stderr are rejected or discarded before canonical projection. Only bounded safe diagnostics and reasoning-token counts may survive.

## Provider fixture adapters

The Codex adapter supports only candidate CLI `0.152.1` with reviewed distribution digest prefix/suffix `b8201824…06f9`. Its fixtures model native lifecycle/final/usage/error items. Reasoning and unrestricted tool output are never projected. The adapter contains no subprocess or network call.

The Grok adapter identifies candidate `1.0.17` with digest `82595e26…4568`. It translates fixtures only and remains `eligible=false` until the same required cancellation, structured output, usage, redaction, isolation, and terminal conformance capabilities are proven. Provider absence/ineligibility yields a typed failure; Codex is not a fallback for Grok and Grok is not a fallback for Codex.

## Brokers and workspace boundary

The note broker accepts concise structured assertions with author role, task/run/packet/fence, evidence references, source digest, type, idempotency key, and bounded body. Corrections append; notes never mutate policy or stage.

The artifact broker accepts only content-addressed references with approved class, repository-contained logical path, SHA-256, media type and byte size. It rejects traversal, absolute paths, symlink/hardlink claims, Git internals, executable classes outside policy, and cross-task handles.

Usage proposals include metering provenance, provider call identity, price-table digest, token categories, cost micros and output bytes. Missing or invalid trustworthy usage blocks another invocation.

Terminal proposals are recommendations, never state-selection authority. The control plane maps allowlisted terminal types through M4's typed transition/retry policy after verifying the current task/run/owner/fence/allocation/packet/deadline/budget.

`WorkspaceBroker` and `GitBroker` are capability protocols. Provider/adapters receive opaque workspace handles, never shared Git paths. The fake runtime models read/write/path/network/environment decisions and makes no OS-security claim. A host capability probe reports whether rootless namespaces, a sandbox launcher and slirp/pasta-style egress boundary exist.

## Persistence, API and lifecycle

Additive migration `014_execution_plane.sql` follows M4's immutable `013_persisted_infrastructure_retry_limit.sql` and creates packet, manifest, stage, canonical event, note, artifact and terminal-proposal tables plus fixed execution metrics. Existing tables/columns/constraints/functions remain unchanged. Runtime gets explicit EXECUTE/INSERT-only capabilities through fixed-search-path functions; no generic DML or policy mutation. Its frozen SHA-256 is `9faa5622cbd66b3c90afd34873e8e17ad24062a2c02036ea86852bdd4c7128d9`; once accepted, execution-plane repair is forward-only as `015+`.

New endpoints are `/v1/execution/claims`, `/v1/execution/stages`, `/v1/execution/notes`, `/v1/execution/artifacts`, `/v1/execution/usage`, and `/v1/execution/terminal`. All use the current actor authentication, body cap, idempotency/correlation boundary, and M4 live-fence checks. `/v1/claims` and its OpenAPI response remain byte-for-byte semantically legacy.

Execution stages are `prepared`, `running`, `collecting`, `completed`, `failed`, `needs_human`, `cancelled`, and `orphaned`. Only the control plane applies transitions. Exactly one terminal stage exists per manifest.

Restart recovery scans at most 100 nonterminal manifests in stable key order under fixed timeouts. A manifest whose M4 allocation/fence is no longer live becomes `orphaned` once, appends bounded safe diagnostics, releases broker-owned fake workspace state, and rejects late proposals.

## M6 bridge boundary

M5 exports only factual, digest-bound bridge inputs: exact head SHA, packet/manifest digests, provider/profile identity, terminal result type, artifact digests, bounded notes, usage and protocol/recovery diagnostics. M6 will define its own semantic finding/verdict schema on its accepted base. M5 neither defines that schema nor treats `run.completed` as acceptance.

The downstream M7-M9 chain is roadmap only and creates no present capability or authority:

```text
M5 exact result/manifest/artifact digests + exact head SHA
  -> M6 exact semantic subject and independent verdict digest
  -> M7 shadow-only ready-for-PR bundle and cohort evidence
  -> M8 >=30 human-accepted outcomes, trust profile/demotion, hard L2 ceiling
  -> M9 exact profile/artifact into preview -> staging -> canary -> recovery
  -> production remains human-owned
```

Every edge binds the exact input SHA and canonical digest. Any changed commit, packet, manifest, result, verdict, cohort, trust profile, artifact, policy, or environment invalidates downstream evidence and requires recomputation from the changed edge. Rollback moves to the last independently accepted exact binding and never promotes stale evidence. No M5 record can mint a semantic verdict, ready-for-PR authority, trust level, deployment approval, external-write capability, or production authority.

## Systemd source topology

Source-controlled predefined units describe one supervisor, one application writer, a fixed reader template whose global/repository admission remains PostgreSQL-authoritative, and local broker services. Unit names, users, commands, environment files, restart rules, limits, address families, filesystem access and capabilities are fixed source, never task data.

Static tests require `NoNewPrivileges`, a private temporary directory, strict protection for system/home/kernel controls, empty ambient capabilities, syscall/address-family restrictions, resource ceilings, bounded restart behavior, and no enable/install command. Units are not installed or activated here.

## Host isolation gate

This host lacks `podman`, `bwrap`, `newuidmap`, `slirp4netns`, and `pasta`; unprivileged user namespace creation returns `EPERM`. Therefore credential and egress OS isolation exit evidence is `BLOCKED` pending a dedicated rootless host. Source, fixtures, fake-runtime, migrations and unit checks can pass without turning that blocker into a skip or claiming M5 exit.

## Verification and documentation parity

Tests cover contracts, JSON/JSONL abuse, adapter exact-version fixtures, no fallback/live-call surface, brokers, fake workspace/Git attacks, additive migration shape, legacy compatibility, execution service/API, recovery/metrics and systemd sources. Root structure/architecture tests require current M5 links and the interface chain:

```text
M4 exact base/state/lease/fence/budget
  -> M5 TaskPacketV1 / ProviderProfileV1 / RunManifestV1
  -> M6 digest-bound semantic bridge inputs
```

The complete root README stack graph remains complete. Historical evidence is not rewritten for current-state wording.

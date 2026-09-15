# Workflow Artifact Adapters Design

## Outcome

Add a deterministic, model-neutral compiler that can ingest explicitly manifested GitHub Spec Kit, BMAD Method, and Superpowers documents as untrusted advisory data, compare them with the native M1/M2/M3 workflow, and emit a stable task graph plus a convergence report. Native `change-spec.yaml`, executable architecture, governance registries, the active route, and external Trust CI remain authoritative.

## Authority and trust boundaries

The compiler is an anti-corruption layer, not another workflow authority. It cannot modify a route, select agents, create approval scopes, activate governance, create receipts, alter Trust CI, or claim merge eligibility. All source files are repository-relative entries in an explicit manifest and are read through a descriptor-bound, no-follow, bounded loader; document content is data and is never executed or treated as instructions.

The compiler performs no network, subprocess, shell, plugin, or LLM calls. RED/GREEN arrays are non-executed metadata constrained to a closed read-only verification-command policy; shell/interpreter code, network tools, URLs, and unknown commands fail closed. CLI/verifier orchestration computes the trusted current fingerprint and canonical receipt bindings outside the compiler. Commands default to read-only. Explicit writes require an active change ID and expected digest and may target only the two derived canonical files `workflow/task-graph.json` and `workflow/convergence-report.json`, or marked advisory files beneath `workflow/projections/` and `workflow/exports/`.

## Canonical contracts

- `WorkflowSourceV1` records `source_type`, `source_version`, repository-relative NFC path, role, byte size, and SHA-256 digest.
- `WorkflowTaskGraphV1` records the canonical change ID, current route writer and at most twenty reviewers, source-manifest digest, and at most five hundred stable tasks. Each task has bounded dependencies, exact AC/INV/FORBID coverage, declared write paths and interfaces, allowlisted non-executed RED/GREEN verification argv, and a `source_status` hint. It never persists a tree fingerprint or receipt-derived authority. Task IDs are content-derived and never include a full-tree fingerprint.
- `WorkflowConvergenceReportV1` records deterministic findings, dispositions, coverage, graph/report digests, and blocking status. Findings cover source drift, task cycles/missing dependencies, write conflicts, missing criteria coverage, disagreement between native and graph source claims, placeholders, goal/AC conflicts, and architecture contradictions. Runtime `effective_status` is computed separately: a complete source claim remains pending until all canonical receipts bind the current orchestration fingerprint, then becomes verified without editing the tracked graph/report.

Canonical JSON uses UTF-8, sorted keys, compact separators, a trailing newline, finite JSON values, and NFC strings. Duplicate JSON keys and unsupported YAML features fail closed.

## Adapter mappings

GitHub Spec Kit uses a closed manifest role set: `constitution` becomes governance candidates only; `spec` becomes requirement/AC candidates; `plan` becomes architecture candidates; `tasks` becomes task candidates; `checklist` becomes convergence hints. A constitution is never active governance.

BMAD uses `prd`/`spec` for requirement candidates, `architecture`/`project-context` for architecture or governance candidates, `epics`/`stories`/`sprint-status` for task candidates and status projections, and `readiness` for convergence hints. Personas, commands, agents, and orchestration are excluded.

Superpowers accepts tracked `spec` and `plan` documents as advisory projections. `sdd-evidence` below `.superpowers/sdd/` is runtime evidence metadata only and can never satisfy native verification or review receipts.

Adapters parse a bounded documented subset of native artifacts without requiring repository-specific annotations: Spec Kit phase headings plus `- [ ] TNNN [P] [USN] ...` task rows, and BMAD story/epic headings, status sections, task checkboxes, and sprint-status key/value hints. BMAD task identity and sequential dependencies reset at each story/epic heading, so independent epics never acquire cross-heading dependencies. Exact `AGB-TASK`, `AGB-CLAIM`, and `AGB-TASK-STATUS` comments are optional closed overrides for fields the native formats do not encode; there is no fuzzy natural-language inference. Missing file, interface, or RED/GREEN detail is explicitly marked `enrichment_required` and blocks convergence rather than becoming silently authoritative.

## Flow

1. Validate the explicit source manifest and no-follow-load every allowlisted file.
2. Normalize sources into `WorkflowSourceV1` and adapter candidates.
3. Compile route-bound tasks and validate the DAG, ownership, commands, interfaces, and criterion coverage.
4. Compare native artifacts, imported candidates, and stored graph/report; descriptor-safely loaded canonical receipts plus the trusted fingerprint supplied by CLI/verifier orchestration determine only ephemeral effective task status.
5. Emit a deterministic report. Blocking findings cause a non-zero validate/converge exit.
6. Optionally publish exactly `task-graph.json`, `convergence-report.json`, or non-authoritative projections/exports. Per-target runtime locks serialize cooperating writers. Missing-target creation is no-clobber; existing-target publication uses an atomic exchange whose immediate preflight identity includes device, inode, mode, size, mtime, and ctime. Post-exchange comparison retains ctime with the platform's monotonic rename transition, and any validation failure rolls back before displaced content inspection. CAS never performs pathname unlink: every stage, expected displaced value, or racing competitor is moved with no-clobber rename to a unique bounded `.agb-recovery-<token>` entry below ignored `.grok-stack/runtime/workflow-cas/<change>/`; if that rename cannot be established, the unique bounded `.agb-stage-<token>` entry remains beside the target. These visible artifacts are forward-recovery evidence, including after successful publication, and are never automatically cleaned by an unproven path identity. Platforms without atomic exchange reject existing-target CAS rather than claiming unsupported filesystem atomicity.

## Compatibility and rollout

The verifier runs the workflow check only when the active change has `workflow/manifest.json`; historical packages remain compatible and report `skip`. Installer and package inventory include the module, CLI, schemas, and tests. Rollback is removal of the opt-in manifest and generated projections; native M1/M2/M3 artifacts are unchanged.

## Security cases

Reject absolute paths, `..`, backslashes/control characters, non-NFC names, case-fold path collisions, duplicate manifest paths, symlinks in every component, FIFOs/devices, file replacement during read, oversized/deep/node-heavy documents, duplicate JSON keys, parser recursion, YAML tags/anchors/aliases/merge keys, unsupported roles, authority-shaped fields, non-allowlisted command argv, unsafe or forged receipts, and CAS digest/identity races. CLI route/change authority pointers use the same descriptor-bound, no-follow, nonblocking regular-file loader and closed shapes. Tests prove no source mutation, no framework-tree mutation, no compiler network/process invocation, deterministic output, serialized cooperating writers, competing-value preservation, and no receipt/approval elevation.

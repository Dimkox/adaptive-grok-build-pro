# Architecture analysis — M1 trust boundaries

## Verdict

**CONDITIONAL GO for implementation under route `a4f88266a848`.** The rebuild package has the correct broad boundary—dual-read/single-write local migration, independent external holdout, data-only trusted extraction, and source-only delivery—but the write owner must adopt the rulings below. Four points are release-blocking if omitted:

1. a modified/new spec can never enter the legacy YAML path;
2. old signed attestations must still verify over their original field set, not merely deserialize;
3. an installed target must receive the schema that its copied CLI imports;
4. source completion must not be reported as deployed holdout/worker completion.

This report is local design evidence only. It is not a receipt, human security approval, deployed holdout, signed attestation, or merge authority. PR/issue/task `#10` was explicitly excluded and contributes no scope or evidence.

## Trust-boundary map

| Boundary | Trusted for | Explicitly not trusted for |
| --- | --- | --- |
| Typed spec in PR/worktree | Declared intent after strict parsing/validation | Instructions, code execution, approval, proof that evidence passed |
| Local validator/CLI/receipts | Developer preflight and deterministic traceability | External merge verdict or human approval |
| Repository `trust-ci/holdout.example/**` | Reviewed source/example and tests | Deployed holdout behavior; PR can modify it |
| Deployed external holdout | Independent critical invariant enforcement under policy-bound digest | Running PR-controlled validator modules |
| Deployed Trust CI worker | Exact-SHA checkout, bounded data extraction, signing and App check publication | Implementing the product change or following spec text as instructions |
| Stored signed attestation | Exact payload that was signed | A normalized/reconstructed payload with fields added after signing |

The assets at risk are repository/host files, spec and contract contents, local evidence integrity, deployed CI keys, signed attestation replay, and branch-protection correctness. Relevant abuse cases are parser ambiguity, legacy-path downgrade, traversal/symlink reads, evidence self-certification, signature invalidation through normalization, and claiming un-deployed code as independent proof.

## Binding rulings

### R1 — Strict parser: dual read must not become downgrade acceptance

Use one bounded byte reader followed by two explicitly selected decoders:

- **canonical decoder:** required for every added/modified spec and for new generation;
- **legacy decoder:** compatibility-only for an explicitly requested unchanged historical file.

The gate, not a field inside the untrusted document, decides whether legacy parsing is allowed. `load_spec()` may expose an explicit `allow_legacy`/profile option, but changed-spec discovery must always pass canonical-only. Never try JSON and silently fall back to YAML for a changed file: malformed JSON would then become a downgrade vector.

Canonical parsing must, before semantic validation:

- cap bytes before decoding; require strict UTF-8;
- reject duplicate JSON keys with `object_pairs_hook` or equivalent;
- reject `NaN`, infinities, BOM/trailing data, and non-object roots;
- bound nesting depth, total nodes, collection lengths, string lengths, criteria/evidence counts, and contract paths;
- reject absolute/traversing contract paths and avoid following symlinks/non-regular files when fingerprinting declared contracts;
- return path-qualified error codes without logging spec content.

The schema-subset implementation must preflight the entire checked-in schema, including unused `$defs`, reject every unsupported keyword, and implement every admitted keyword. A validator that checks unknown keywords only along instance-selected branches can silently drift from the schema.

Define deterministic authoring separately from semantic hashing:

- writer: one JSON serializer and one terminal newline;
- semantic digest: SHA-256 of compact, sorted, UTF-8 canonical JSON;
- malformed provenance digest: SHA-256 of bounded raw bytes, never counted as valid/mapped evidence.

Generation must serialize a Python object, not interpolate raw route text into quoted JSON. Route tasks can contain quotes, backslashes, newlines, and Unicode. Only `objective.success_metric` and `objective.target` may be `UNKNOWN` in a draft; rollback remains schema-valid.

### R2 — Legacy compatibility requires a real contract boundary

The existing published prototype identifies itself as `schema_version: 1` / `urn:adaptive-grok:change-spec:v1`, but the approved final model changes evidence from `{kind, ref}` to exactly-one-key references, removes/adds evidence kinds, and introduces `SIG-*` semantics. Silently assigning those new meanings to the same v1 identifier is a breaking contract even if unchanged repository files are skipped by the gate.

**Preferred ruling:** freeze the existing v1 schema/reader for historical explicit reads and issue the strict canonical model as change-spec v2. New generation and this active package use v2. The attestation payload version is a separate contract and may remain 1.

If the approved scope insists that new specs remain change-spec v1, then the final v1 schema must preserve the old data model; canonical JSON may change only serialization. Do not combine a new evidence model with the old version identifier. This decision must be settled in Task 1 before CLI, receipt, holdout, or runner fixtures are written.

Keep compatibility helpers/CLI aliases only as adapters around one internal validator. The current and planned `validate_spec` signatures and return types are incompatible; do not silently replace them without dispatch/alias regression tests. Legacy reads may summarize historical records, but cannot produce current gate evidence.

### R3 — Typed evidence is a declaration, not proof

`criterion_coverage` means declaration coverage: total criteria, criteria with at least one structurally valid reference, unmapped IDs, and counts by evidence kind. It must never be labeled as criteria proven or passed.

- `production_signal` references resolve to stable `SIG-*` observability IDs.
- Receipt and attestation references use a bounded vocabulary/format.
- A nonexistent arbitrary test path must not silently become “independent evidence”; at minimum validate its normalized repository-relative file portion when it is expected to exist.
- Typed `approvals.required_scopes` are descriptive. They cannot mint, waive, or replace deployed-policy approval requirements.

The active route is high risk, so its final typed tier is **red**, not the earlier plan's yellow. It therefore requires explicit forbidden outcomes and at least one descriptive approval scope. Changes under `trust-ci/**` and `.grok-stack/**` will independently cause the deployed policy to decide whether an externally signed `governance` scope is required.

### R4 — Receipt binding belongs in the central writer

Current `write_receipt()` has many callers that do not know the spec. If only verification passes new fields explicitly, code/test/security/release review receipts remain unbound. The central receipt writer must resolve and bind the current active valid spec by default:

- sorted/de-duplicated `criterion_ids` for criteria declaring `receipt: <kind>`;
- active spec semantic digest;
- active spec fingerprint;
- exact Git HEAD and current tree fingerprint already represented by the workflow.

Explicit fields may be supplied by verification, but inconsistent explicit/current values fail rather than overwrite silently. Old receipts remain readable historical records; when the active spec requires criterion binding, missing digest/fingerprint fields make an old receipt insufficient for the current gate.

Compute all bindings from one stable snapshot: obtain fingerprints, write atomically, then confirm the tree/spec did not change during construction. Single-write-owner policy reduces races but does not remove TOCTOU risk from editor/test processes.

`validate_evidence()` must reject:

- wrong route/kind/status;
- stale tree or spec fingerprint;
- missing required current-spec binding;
- criterion IDs not present in the current spec or not mapped to that receipt kind.

A failing verification still needs a bounded report/raw digest; receipt construction must not crash because the spec is invalid. Local receipts remain advisory even when perfectly bound.

### R5 — Verification must gate active plus changed specs without trusting runtime state externally

Local fast mode performs draft validation. PR/release mode requires the active spec and canonical-gate-validates every added/modified spec. Multiple changed specs are sorted deterministically. A standard/high-risk product change without a valid active spec fails closed.

The documentation-only micro exemption is local because it uses the route. It is valid only if every predicate is true and the report names the exemption. The external holdout cannot claim to have independently proven `.grok-stack/runtime` route complexity; that state is absent from the exact checkout and is not trusted merge input.

### R6 — Holdout independence is behavioral and operational

`trust-ci/holdout.example/change_spec_validate.py` must be a separate stdlib implementation. It may share golden input/output fixtures, but cannot import `.grok-stack/adaptive_grok/spec.py`, its schema executor, or any PR-controlled module.

In deployed mode, exact valid `TRUST_CI_BASE_SHA` and `TRUST_CI_HEAD_SHA` plus a successful NUL-delimited git diff are mandatory. “Where possible” fallback is fail-open. Diff failure, a deleted required spec, unreadable/non-regular path, malformed JSON, duplicate key, invalid IDs/evidence/signals, or incomplete red controls is a holdout failure.

Tests must execute the holdout against temporary git histories and cover missing/bad SHAs, diff failure, deletion, multiple specs, unchanged legacy exclusion, canonical downgrade attempts, symlinks, size/depth limits, and no local-validator import. Source-string assertions alone are insufficient.

The checked-in example is not the deployed holdout. Task 4 proves source readiness only; it cannot satisfy the external-holdout M1 exit criterion until a human-controlled rollout installs the reviewed bundle and binds its digest into deployed policy.

### R7 — Trusted runner extraction must be host-safe

The metadata helper executes in the privileged trusted worker, not merely inside the no-network runner. For each changed path supplied by the trusted checkout component:

- accept only normalized `engineering/changes/<one-directory>/change-spec.yaml` paths;
- prove containment below the checkout;
- reject symlinks and non-regular files using no-follow semantics;
- cap file count/size/depth and catch decode/JSON/recursion/I/O errors;
- never execute/import checkout code and never log payload contents.

A PR-controlled symlink followed by host-side `Path.read_bytes()` could expose host files to hashing/logging and crosses the trust boundary even if the holdout container itself is isolated.

Use named, golden-tested digest algorithms. Recommended composite input is sorted canonical JSON entries containing path, raw byte digest, and canonical semantic digest or `null`. This supports provenance for malformed files without pretending they are valid. Local and Trust CI code implement the same vectors independently.

### R8 — Signed attestation compatibility means verifying the old signature

Current verification parses an envelope and verifies `canonical_json(parsed.payload.to_dict())`. If `from_dict()` defaults absent metadata to `None`/empty coverage and `to_dict()` emits those new fields, the bytes differ from the old signed field set and every stored legacy signature fails.

Implement one of these safe patterns:

1. verify a mapping envelope over the original payload mapping first, then normalize it; preserve that original mapping/presence through PostgreSQL retrieval and replay; or
2. preserve per-instance field presence and make legacy `to_dict()` omit fields that were absent when parsed.

Do not test only `from_dict()`. Commit a pre-M1 signed golden envelope and prove:

- mapping verification succeeds;
- store/PostgreSQL load retains verifiability;
- runner replay republishes the stored result without checkout;
- payload tampering still fails;
- new metadata fields are covered by new signatures.

`criterion_coverage` must be a strict bounded object with exact keys, nonnegative non-boolean integers, stable sorted unique IDs, and no arbitrary nested data. `spec_digest`, when non-null, is exact lowercase SHA-256.

Backward compatibility is two-directional operationally. The current old reader ignores unknown fields while reconstructing known fields, so it cannot verify a new signature that covers added fields. Before any production emitter writes new payloads, deploy a compatibility reader capable of old and new verification. The rollback target after emission starts must retain that reader.

### R9 — Installer/schema delivery is part of M1, not packaging trivia

`install_into.py` currently copies `.grok`, `.agents`, `.grok-stack`, and selected scripts, but not root `schemas/`; copied `spec.py` resolves `<target>/schemas/change-spec.schema.json`. The installed CLI is therefore incomplete even though the full release archive contains the schema.

Add the versioned change-spec schema file(s) to the managed install set and conflict/force semantics. An installer test must create a clean target, assert the schema bytes were copied, and invoke the installed target's `scripts/grok_spec.py` with the source checkout removed from `sys.path`/resolution. Current patched CLI tests can accidentally use the source checkout's schema and do not prove delivery.

Do not copy Trust CI deployment or holdout runtime into ordinary consumer repositories; external Trust CI remains independently installed.

### R10 — Source completion and deployed completion are separate states

The source PR will be evaluated by the currently deployed worker and holdout. It cannot make that already-deployed runtime emit or enforce code introduced by the same PR. A green existing policy-epoch check proves the source passed current trust policy, not that new attestation metadata or new holdout behavior is live.

Required staged rollout after source merge, under separate exact operator authorization:

1. independently build/review/pin the merged worker artifact and external holdout bundle;
2. deploy the new compatibility reader with metadata emission disabled;
3. canary old signed-attestation verification/replay and canonical-spec holdout behavior;
4. enable new metadata emission, update the holdout/policy digest, and observe the new App-owned policy-epoch check on an exact disposable PR SHA;
5. verify the new signed attestation offline;
6. only then retarget branch protection and record operator-safe evidence in a follow-up PR.

Task 6 may mark local/source work items complete after final-tree tests and reviews. It must leave deployed holdout/attestation exit items open until the rollout proof exists. README/roadmap wording must distinguish those states.

The current rollback statement that “new optional metadata can be ignored by old readers” is false for signed payloads under the current verifier. Correct rollback behavior is:

- before deployed rollout: revert source through the protected PR path while retaining the old deployed runtime;
- after compatibility-reader deployment but before emission: disable emission and retain that reader;
- after new signatures exist: never roll back to the pre-M1 reader; prefer forward fix, or restore a compatible reader plus reviewed old holdout/policy, obtain a fresh policy epoch/canary, and retarget branch protection only after proof;
- never delete or rewrite stored attestations.

## Task dependency and completion rulings

| Task | Must be settled before it | Completion evidence |
| --- | --- | --- |
| 1 schema/parser | v1-versus-v2 compatibility decision; canonical and legacy profiles | adversarial parser limits, schema preflight, legacy downgrade exclusion, golden digests |
| 2 generation | Task 1 final model/writer | hostile route strings serialize safely; new package canonical; Markdown authority notice |
| 3 CLI/receipts | Task 1 digest/fingerprint/coverage and Task 2 active-spec resolution | installed/explicit CLI, central receipt binding, stable-snapshot staleness |
| 4 holdout | Task 1 golden critical invariants | independent behavior over exact git histories; source-ready only |
| 5 attestation | Task 1 composite vectors and Task 4 malformed semantics | old signed golden verify/store/replay; host-safe one/many/malformed extraction |
| 6 package/evidence | Tasks 1–5 final interfaces | active red-risk canonical spec, root/Trust CI suites, compileall, PR verification, code/test/security/release reviews on one fingerprint |

Any application/package/README/roadmap change after receipts or review invalidates the local evidence and requires re-verification/review. The baseline prototype tests passing is characterization evidence only; it does not prove these M1 boundaries.

## Non-goals preserved

- No M2–M9, `factory/`, scheduler, systemd, backend/model field, multiple writers, autonomous external write, or root dependency manifest.
- No GitHub Actions, deployed policy/holdout/image/trust-store/key/branch-protection mutation, or human private-key handling.
- No mass rewrite of unchanged historical packages.
- No use of local receipts, Markdown, PR-controlled holdout source, or agent review as authoritative merge trust.

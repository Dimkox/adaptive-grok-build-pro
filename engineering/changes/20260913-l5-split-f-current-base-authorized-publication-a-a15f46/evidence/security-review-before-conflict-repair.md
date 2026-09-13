# Independent security review — L5 split F current base

Verdict: **FAIL**. SEC-F-01 is a blocking supported-schema/data-integrity defect: an accepted lookalike schema can replace a durable publication intent instead of rejecting conflicting reuse of its request ID. No claim of a remote exploit or demonstrated bypass of an external-write grant is made.

## Reviewed identity and evidence

- Read-only source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f2`.
- HEAD: `5a2ead6e6e1eff5c5df28a8d4bcb91a209975187`.
- Route: `a15f467e4575`; genuine base: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Recomputed tree fingerprint: `939cd5d8b4cf7af62b8a275faef0e791a8645cea3e7e4a1e065aa2a06a2698f5`.
- Prescribed verifier `/tmp/agbp-sweep/split-f2-full-final.json`: all 15 checks PASS, created `2026-09-13T15:14:49+00:00`, SHA-256 `991a7850b0ac73ca06a802afe962491487f4d22540cfdd48e29bf8b0df7c89ea`. Matching full verification does not invalidate a subsequently reproduced review defect.
- Source was clean at identity verification. This reviewer made no source/test/configuration changes or approval receipts.
- Independent disposable reproduction `/tmp/agbp-sweep/split-f2-security-conflict-policy.json`: SHA-256 `6a4939d9b061ed37c40817fd9626858afdfa20d4808d49d55fcff2b8ddcd8dfc`. Only temporary SQLite databases were opened; no target publication, authority call, credentials or network was used.

## SEC-F-01 — P2, blocking: accepted conflict policies break intent immutability

Location: `delivery/src/adaptive_delivery/landing_publication.py:35` (`_validate_schema`), with the effect at `PublicationStore.prepare`, line 175.

The validator correctly checks table inventory, STRICT/rowid flags, column types/nullability/defaults/primary-key positions, foreign-key absence and both BINARY unique-index signatures. SQLite's inspected PRAGMAs do not disclose the constraint's `ON CONFLICT` policy, and the current predicate never inspects the table declaration for that remaining semantic difference.

Reproduction on the reviewed HEAD:

1. Create a temporary private publication database with application ID `0x4C355055`, user version 1 and the shipped `_SCHEMA`, changing only `request_id TEXT NOT NULL UNIQUE` to `request_id TEXT NOT NULL UNIQUE ON CONFLICT REPLACE`.
2. `PublicationStore(root)` accepts it.
3. Prepare a valid stage request with ID `same-request-id`, then another valid request with the same ID and a different paired baseline release/manifest, hence a different request digest.
4. The second `prepare` succeeds and the first durable row disappears. Expected behavior is rejection with `publication_idempotency_conflict` and preservation of the original intent. A second fixture with `ON CONFLICT IGNORE` also passes validation and produces `publication_request_unavailable` instead of the specified conflict classification.

The demonstrated REPLACE result retained only digest `a58b5f8b6f314d426adf6b5e264f900425cdda27a70a7b5896b1a6a9b4050ec3`; original digest `d96460a2f8304d0256f3641aa5005effffc5481c20764da8000ee5888560d71e` was removed. Inputs were valid `PublicationRequestV1` objects. The ordinary supported schema is already covered by a regression that expects this direct store operation to reject conflicting reuse.

Practical boundary: the current coordinator performs a `find_id` precheck before calling this store method, and state files are private owner-controlled files. This reproduction is therefore a supported-store/schema-contract failure, not proof that an untrusted HTTP actor can rewrite an intent or that the CLI performs an unauthorized filesystem effect. Those bounds do not satisfy the explicitly added fail-closed supported-v1-schema requirement: silently replacing historical intent records defeats the durability/idempotency property this repair claims to enforce.

Required correction: add RED fixtures for unsupported UNIQUE/PRIMARY KEY conflict policies in writer and read-only opens, then bind the actual table declaration's remaining semantics to the supported v1 declaration. A narrow option is to retain the existing PRAGMA checks and compare the stored CREATE TABLE declaration with the shipped one under explicitly bounded whitespace normalization; the shipped historical declaration and current supported fixture differ only in indentation. Reject unknown policy additions without migration or mutation of existing rows. Do not add a broad SQL parser/framework or weaken acceptance to preserve the existing verification. `INSERT OR ABORT` alone can protect one write but does not complete the claimed supported-schema identity check.

After the sole writer repairs this defect, the changed source needs fresh prescribed verification and the route-selected independent reviews before a current PASS can be recorded.

## Other security boundaries inspected

Read the active route, current change brief/requirements/architecture/test plan, actual eleven-path F product delta and surrounding implementation. Reviewed `landing_filesystem`, publication contracts/store/coordinator, Factory publication CLI, repository wrapper, request schema ownership and relevant direct filesystem/authority/recovery regression tests.

The repository wrapper requires the exact repository identity, active route/change, current HEAD and tree fingerprint, exact `external-write` scope/action list and one exact request resource, a valid delegated-consent source, bounded lifetime and exactly one matching grant. Resource identity includes action and the digest of the complete request, thereby binding target, artifact/reference, desired state and baseline. It returns a hash for retention, not raw grant data.

The CLI rejects missing live enablement or missing callable authority before configuration/state access. Actual grant validation occurs after loading the persisted request, target observations and required retained artifact, and before the inflight transition and transport effect. Observation-only outcomes may update local intent records without acquiring a grant; this behavior is explicit and does not replay writes.

Artifact loading checks configured tenant/repository scope before reading state, uses parameterized read-only SQLite queries, preserves WAL visibility, validates source/retained artifact bindings and rejects overlapping control/state/deployment/output roots. Digest-addressed release members are verified against retained manifest/archive data; permitted paths are canonical, bounded and relative. The filesystem adapter traverses through no-follow directory descriptors, binds target UID/device/inode, checks a pre-existing owner lock, rechecks baseline under exclusive lock and rejects symlink/hardlink file substitutions. It freezes release files/directories and atomically replaces only the local current pointer, with fsync ordering.

The intent moves to `inflight` with the grant digest before filesystem effects. Errors after that point produce observation-only reconciliation; ambiguous or unavailable observations become `needs_human` without replay. Restore preparation requires an observed currently active successful activation and uses its prior baseline. The supplied current tests exercise committed stage/activation followed by store reopen, interrupted pointer changes, empty/prior-release restore and stale lineage rejection.

These reviewed boundaries showed no additional blocking authorization, path traversal, network-exfiltration or recovery-replay defect. They do not cancel SEC-F-01.

## Limits and inherited observation

This review covers source extraction, local authority enforcement and owner-controlled filesystem semantics. It does not establish externally reachable HTTPS behavior, production host access, remote publication, real grant eligibility or approval validity outside the local workflow. The public origin is metadata and remains explicitly `http_origin_verified=False`.

No real credentials, deployed Trust CI policy/state/holdout/signing material, human private keys or operational target were accessed. There was no external write, provider call, approval materialization, merge, tag or deployment. Local review evidence never replaces the GitHub App-owned exact-SHA policy-epoch check or required external signed approvals.

Inherited D observation SEC-D-01 (malformed SSE scalar types may raise `TypeError`; the service still rejects and purges) is unchanged by F and remains an explicitly known nonblocking decoder issue. The independent D report documents that evidence and its limits. No new current-provider or moderation claim is made here.

# Independent security re-review — corrected L5 split F

Verdict: **PASS**. SEC-F-01 is closed on the exact source below. No remaining blocking security finding was identified in the F slice. The earlier FAIL remains historical evidence and is not relabelled as a pass.

## Exact identity and verification

- Source, reviewed without edits: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f2`.
- HEAD: `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`.
- Route: `a15f467e4575`; genuine base: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Recomputed tree fingerprint: `aa60705bc8c9bbae34517a480ed842254c8b67db86b8b0a6cd3a119b6740cff5`.
- Current prescribed full verifier: `/tmp/agbp-sweep/split-f2-full-final.json`, created `2026-09-13T15:39:48+00:00`, status PASS across all 15 recorded checks; SHA-256 `fd576951dd5cebfc1ab59a0de3d70b22495c235f03731a1db80c6fcd2e3dcdd6`. The report's route and fingerprint match this tree.
- The earlier review of `5a2ead6e6e1eff5c5df28a8d4bcb91a209975187` remains in `security-review-before-conflict-repair.md`. Its original reproduction is preserved as `split-f2-security-conflict-policy.json`; old full verification/reviews are historical, not current acceptance.

## SEC-F-01 closure

The original validator could accept a STRICT table with `request_id UNIQUE ON CONFLICT REPLACE` because the inspected PRAGMAs did not expose the conflict policy. A direct store preparation could then silently remove a prior durable intent with the same request ID. `ON CONFLICT IGNORE` likewise produced an unsupported classification. That was a supported-schema/idempotency failure; the review did not demonstrate an external-write authorization bypass.

The current repair first compares the complete stored CREATE TABLE declaration to the shipped v1 declaration under whitespace collapse and case folding. It retains all prior table, column, index, foreign-key and schema-inventory checks. Comments, quoting, extra clauses and conflict-policy tokens remain significant and reject. The creation `_SCHEMA`, application ID, user version and existing supported record shape are unchanged; no migration is introduced. `INSERT OR ABORT` makes the insertion conflict behavior explicit as an additional defense.

The repair is intentionally restricted to the supported application-generated v1 declaration, including the tested case/whitespace variation. It does not claim to recognize arbitrary equivalent hand-authored SQL. Alternate quoted/commented declarations fail closed rather than being silently migrated or stripped into apparent equivalence.

Reviewed new regressions cover UNIQUE and PRIMARY KEY REPLACE/IGNORE policies in both writer and read-only mode, comment/quoted/bracketed variants, supported formatting compatibility, and seeded-original-intent preservation. Archived RED output reports 18 failed subcases on the pre-repair code; current focused GREEN reports 20 tests plus 88 subtests passed. Current full verification subsequently passed on the frozen repaired commit.

Independently reran the original failure class using temporary SQLite databases on the current HEAD: all eight UNIQUE/PRIMARY KEY × REPLACE/IGNORE × writer/read-only opens returned `publication_state_schema`. A supported-v1 control rejected conflicting reuse with `publication_idempotency_conflict`, retained the original row and reopened with the same request in both modes. Result: `/tmp/agbp-sweep/split-f2-security-conflict-rereview.json`, SHA-256 `f7621bef64bb09d03bc9177eb60699fc5ddde3981e37b6077181e5f8e91ee939`. These checks made no filesystem publication, grant, credential or network operation.

## Actual scope and surrounding boundaries

Re-read the active route and actual repaired diff, then compared the surrounding security scope with the earlier independent inspection. Relative to the prior reviewed F commit, exactly two product/test paths change: `delivery/src/adaptive_delivery/landing_publication.py` and `factory/tests/test_landing_publication_cli.py`. Other differences are the disclosed change package, archived evidence and shared mistake record. All eleven SHA-256 entries in the current F source manifest were independently checked against actual files. The manifest correctly states `archive_equivalent=false`; nine F paths remain exact archived blobs and two carry the disclosed conflict-policy repair. Its pre-commit `checkout_head` is provenance, not this report's current HEAD.

The unchanged reviewed boundaries remain relevant to current PASS:

- The governance wrapper binds exact repository/route/change/current HEAD/tree fingerprint, explicit `external-write` scope and action list, one complete request resource, valid delegated-consent source, lifetime and exactly one matching grant. The request resource includes action and a digest covering target, artifact reference, desired state and baseline; the wrapper retains a grant digest instead of exposing raw grant data.
- Apply requires explicit live enablement and a callable authority before configuration/state access. Actual grant validation follows the persisted request, observations and required retained artifact checks, and precedes the inflight transition and filesystem effect. Observation-only results may persist local state without a new grant; they do not replay an effect.
- Factory artifact loading checks configured tenant/repository scope before state access, uses parameterized read-only SQLite queries with WAL visibility, validates retained source/artifact relationships and rejects overlapping state/control/deployment/output roots. The bundle verifies bounded canonical relative member paths, expected archive/member metadata and content digests.
- Filesystem publication traverses private no-follow directory descriptors, binds target UID/device/inode, verifies the owner lock, checks baseline again under an exclusive lock, rejects substituted symlink/hardlink release files and atomically changes only the configured local current pointer with durability operations. No remote path, shell transport, provider request or hosting discovery is introduced.
- Before any effect, the coordinator durably records `inflight` and the grant digest. Failure after intent leads to observation-only reconciliation, with `needs_human` for ambiguity/unavailability and no replay. Restore preparation requires a matching successful activation/current observation and uses its recorded earlier baseline. Existing tests cover interrupted pointer changes, committed stage/activation followed by store reopen, empty/prior-release restore and stale-lineage rejection.

## Limits and authority

This is independent source/security review plus bounded disposable SQL regression checks, not production publication acceptance, a remote penetration test, a dependency vulnerability audit or a current model/moderation probe. The supported model assumes an owner-controlled host and private directories; a malicious same-UID operator is not treated as an isolated remote actor. `http_origin_verified=False` remains accurate: local pointer/file observation does not prove externally reachable HTTPS behavior.

The inherited D observation SEC-D-01 about malformed SSE scalar types remains unchanged by F and is documented separately: the service rejects the malformed result and purges input, but decoder error classification may be generic. It is not a new F blocker and this report makes no new live-provider claim.

No source files, credentials, operational publication targets, deployed Trust CI policy/state/holdout/signing material or human approval keys were changed or read by this reviewer. No external write, provider request, approval materialization, merge, tag or deployment was performed. No self-approval receipt was recorded. Local PASS remains preflight evidence and cannot replace the GitHub App-owned exact-SHA policy-epoch check or separately required signed approvals.

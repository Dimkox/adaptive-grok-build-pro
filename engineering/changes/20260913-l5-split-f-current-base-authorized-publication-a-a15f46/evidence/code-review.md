# Independent code review — split F2, repaired conflict-policy boundary

Verdict: PASS for the bounded offline publication/intents/authority slice at the exact source below. No blocking correctness or security finding identified in the actual current implementation. This is the first code-review report for F2; prior independent security/data FAIL reports and initial full-pass evidence remain historical and are not overwritten.

## Identity and inspected scope

- Route: `a15f467e4575`; change: `20260913-l5-split-f-current-base-authorized-publication-a-a15f46`.
- Immutable source HEAD: `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`.
- Genuine route and stacked-PR predecessor: E `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Independently recomputed clean-tree fingerprint: `aa60705bc8c9bbae34517a480ed842254c8b67db86b8b0a6cd3a119b6740cff5`.
- Independent reviewer: `code_reviewer`; sole product/test owner: `data_implementer`.
- Completed verifier file SHA-256: `fd576951dd5cebfc1ab59a0de3d70b22495c235f03731a1db80c6fcd2e3dcdd6` (`split-f2-full-final.json`).

Read the actual active route, reviewer role, package requirements/architecture/test plan/rollback. Inspected all eleven product/test paths below, the complete publication contract/store/coordinator/filesystem/CLI/wrapper implementations and all twenty new test methods. Inspected surrounding retained-artifact/SQLite usage and the existing `add_approval` issuer source, including its action set, document shape and private atomic file writing. No actual approval store or credential was read, and no approval was generated.

## Correctness and security findings

**Supported schema is closed, including conflict policy.** PublicationStore requires its exact application ID/version and supported v1 CREATE TABLE declaration, normalized only for case/whitespace. The retained PRAGMA checks independently bind STRICT/rowid shape, column order/types/nullability/defaults/hidden flags, the two exact primary/unique index signatures and absence of foreign keys or extra application objects. Thus UNIQUE/PRIMARY KEY `ON CONFLICT REPLACE` or `IGNORE`, comments/quoted alterations and additional triggers do not pass merely because column/index PRAGMAs look equivalent. `INSERT OR ABORT` separately prevents replacement/ignore behavior for prepare insertion. Duplicate IDs either return the byte-identical prior request or reject; no migration or rewrite of an existing intent is used to reconcile a collision. Unsupported schemas remain available for diagnosis; this is a deliberately closed supported format, not general DDL equivalence.

**Durable intent precedes filesystem effects.** Requests bind their action, target, artifact/reference, desired release/manifest, baseline and restore lineage into a versioned digest/resource. Prepare snapshots current state and sealed artifact facts without publishing. Apply loads the stored request, validates the target and current observation, revalidates the artifact, obtains the exact authority digest, and persists `inflight` before stage/activation. Compare-and-update includes the expected phase and canonical request body. A process interruption leaves a durable inflight record; a later apply/reconcile observes filesystem state and records success or `needs_human` without replaying the effect. The tests inject interruption after a real committed stage/activation, reopen the actual SQLite store and prohibit calls to mutation seams during reconciliation.

**Observation-only transitions are intentionally distinct from effect authorization.** Direct CLI `apply` requires `--live` and a callable authority before configuration or state access. Actual grant validation occurs only after saved-request/target/artifact observations and before inflight/effects. Already-achieved, baseline-drift and inflight reconciliation paths may update the local intent without invoking the grant callback; they perform no publication effect. No claim is made that every local bookkeeping write requires an external-write grant.

**Filesystem publication is confined and integrity-checked.** Target identity pins owner/device/inode; private descriptor walks reject links/untrusted writable ancestry and `//` aliases. Locks are nonblocking, owner/type/mode/link/inode checked. Stage validates the archive and canonical artifact/manifest binding, each member path/size/hash/Git-object/provenance, exact archive inventory and expansion bounds; it exclusively creates a new release and freezes files/directories after fsync. Partial stages are preserved rather than resumed or overwritten. Observe checks staged content again with no-follow file access, ownership/modes, complete inventory and hashes. Activation rechecks the baseline under the target lock, verifies the desired staged manifest and atomically replaces the relative current symlink; restore uses only the predecessor captured by a completed activation. Empty-baseline restore removes only the expected current pointer. Pointer failure and committed-but-unobserved effects are reconciled without replay.

**Authority is exact and issuer-compatible.** The repository wrapper checks current active route/change, a canonical exact repository remote, current Git HEAD/tree fingerprint and one uniquely matching delegated local grant. It requires `external-write` as both scope and sole action, the one exact request resource, accepted consent source, grant ID and a valid non-future interval bounded to one day. Foreign/stale/duplicate/broader grants reject before the inflight transition. HTTPS, SCP-style SSH and ssh:// GitHub remote forms are accepted only for the exact repository; suffix hosts and doubled `.git` do not alias it. The shape matches the existing local issuer, whose atomic mkstemp write is mode 0600. This authorizes only the named local operation and cannot establish external App merge trust or human-signed approval.

**Factory integration remains offline and scoped.** The CLI reads the requested tenant/repository/job from a read-only SQLite snapshot, validates retained source/artifact/envelope/file integrity and matching public origin, and keeps artifact output apart from control/state/deployment roots. Publication target/state/config paths reject ambiguous `//` anchors. Status opens state read-only without creating a missing database/lock; observation verifies only the configured filesystem target. The CLI reports `http_origin_verified: false`; no HTTP reachability or web-server configuration is inferred from a pointer change. The repository wrapper injects authority into the actual CLI; no new factory console-script dependency is introduced. Tests bootstrap the existing sibling source trees only for local tests.

The architecture delta declares the request schema under staged delivery and the new factory CLI under the offline landing boundary, bringing the actual landing inventory to 21. It retains the exact `urllib.parse` exception and adds no broader urllib/network permission. G backup and operator templates are not assumed by this slice.

## Verification examined

The fresh completed full verifier is PASS for the exact route, HEAD and fingerprint above: all architecture/drift/diagram, governance, contract/static/security, coverage and source-stability checks pass; core 653, factory-unit 51, PostgreSQL suite 675 run with one skip and two actual restarts, exact roles and recovery/reconciliation. Historical initial full-pass evidence did not prove the conflict-policy guarantee and is not reused as the repaired-source result.

Independent bounded rerun: the three conflict-policy regression methods passed in 0.213 seconds. They reject UNIQUE/PK REPLACE/IGNORE plus comment/quoted variants in writer and readonly modes, preserve supported case/whitespace declarations, and verify that altered-policy opens cannot replace the prior durable row. The other actual twenty-method publication regression assertions were reviewed, including tamper containment, scope rejection, private file/link protection, pointer ambiguity, reopen reconciliation, predecessor/empty restoration, authority/config ordering and exact-grant rejection. No full suite was repeated by this reviewer.

## Limits and recovery

This PASS is local independent code-review evidence for F2 only, not merge or operational authority. Owner-controlled roots, process identity and configured web-server access remain operator responsibilities; chmod-based immutability does not defend against a malicious process with the same OS identity. No public origin, cPanel operation or live site was contacted. Reverting source does not reverse a pointer; recovery preserves SQLite/WAL/staged files and uses observation plus separately authorized predecessor restoration. Other selected security/data/test/release reviews remain independent requirements. This reviewer made no source edit, real grant/credential access, production mutation or external write.

## SHA-256 inventory of all eleven product/test changes

- `architecture/rules.yaml`: `8dee19526f86a19a9605e6b03765af970768d0aeb975eb2a33ddff99f6da34fb`
- `architecture/system.yaml`: `31f7287fe41d860a78354e2f1817b9629972e9021e68fd2ce1d8fec62fdf6361`
- `delivery/contracts/jsonschema/landing-publication-request.v1.schema.json`: `410dd65aa998765155dfda257551ecc1326592d2efc55759f7a04c415937ef28`
- `delivery/src/adaptive_delivery/landing_filesystem.py`: `ba8f64de4d47a08c48fcdd2929ec4076be27a56315237c20cee66efde936a9f2`
- `delivery/src/adaptive_delivery/landing_publication.py`: `e17cdf766e17ad8da5136a70bc457e0caddadc44746efa8b239b2c5b2396aebb`
- `delivery/src/adaptive_delivery/landing_publication_contracts.py`: `9e2b0078e39b56928ca854b69d2563e1d5785d37d7c24736991a0dfaba275a9a`
- `factory/src/adaptive_factory/landing_publication_cli.py`: `f2540419d229ec9a2e653e778da5524549946071f1e4a5271a816d66c59faa31`
- `factory/tests/__init__.py`: `c06f966e59d3defd98992ccf5a9df9ea69ba807c9269a2344b5c1b839bb4b5a7`
- `factory/tests/test_landing_publication_cli.py`: `e7575e3abd1d1f68af83f2728b82945c14750fe0b057cf38b9bbf8ed27877b7f`
- `scripts/grok_landing_publish.py`: `7d13529a5b3418238fc10d1521bf8a2f0b4e04dff078c48f95e8a0c6a8261cea`
- `tests/test_landing_architecture_boundaries.py`: `31f5ab4c96265966e78c4556ae17dcf6795c5d183ac656492c99d922588e57ed`

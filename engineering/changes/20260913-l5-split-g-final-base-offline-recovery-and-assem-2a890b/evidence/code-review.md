# Independent code review — final split G3

Verdict: PASS for the bounded offline recovery, inactive runtime templates and final assembly slice. No blocking correctness or security finding identified in the actual current G implementation. Preserved C/D/F repairs and the documented residual D P3 remain correctly distinguished from new G behavior.

## Exact identity and scope

- Route: `2a890b6485a5`; change: `20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b`.
- Immutable source HEAD: `e6a813e4c16543f262ced2d9ea353caaad9452d1`.
- Genuine corrected F predecessor: `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`.
- Independently recomputed clean-tree fingerprint: `d462d16bbd7f26d6f2dac6fc4b2ae4c5b9bc44d437898297cf3ca524c7b0028b`.
- Independent reviewer: `code_reviewer`; sole product/test owner: `data_implementer`.
- Completed verifier file SHA-256: `7c9ff5a6340c93fe595e5dfefca996610ec0f2308300baed7c752a500f764a99` (`split-g3-full-final.json`).

Read the actual active route, reviewer role, typed requirements, architecture/test plan and rollback. Inspected all ten G product/test paths against corrected F, the complete backup module/tests, final Qwen recovery test tail, inactive installer/service/config templates, architecture inventory and surrounding host/SQLite/publication contracts. Reviewed current README/START_HERE/PROJECT_STATE changes, factory documentation, runtime/publication runbooks, product-disposition list and the documented nonblocking D observation. Prior G2 analysis/test logs were treated as historical component evidence, not current G3 acceptance.

## Findings and reasoning

**Cooperative ownership and standalone database snapshots.** Before creating a snapshot destination, backup validates the configured roots and disjointness from its data/control/source roots, then acquires the same process-lifetime landing and publication writer locks used by the runtime/coordinator. A live cooperative owner rejects before destination creation; failure unwinds acquired locks. SQLite is opened read-only/query-only with trusted schema disabled and the expected application/version identity. The backup API includes committed WAL-visible pages, then normalizes the destination to DELETE journaling before final hashing; source WAL/SHM are not naively copied. Optional publication state and exact retained archive/sidecar names are the only other captured payload. It does not import host/live composition, recover jobs, acquire model credentials, copy raw quarantine/scratch/source data, or snapshot the external deployment pointer.

**Bounded copying and manifest integrity.** Files must be owner-controlled mode-0600 regular single-link leaves. No-follow opens, pre/post descriptor metadata comparison, bounded streaming/hash/count checks, exclusive destination creation and fsync protect the copy from accepted link replacement or unnoticed content change. The manifest records exact original roots, closed inventory, sizes/digests and explicit no-replay/no-publication-target flags, and is written last. Partial destinations are deliberately preserved after failure; they are not reported as completed snapshots.

**Restore budget repair is correctly placed.** The same Budget tracks hash verification and the second copy pass under the unchanged 4 GiB byte accounting and 180-second deadline. After verifying every recorded file and required landing database, preflight checks `budget.total + sum(entry sizes)` before creating any destination root. The guard does not double the cap or reset its accounting. The reduced-cap regression demonstrates that backup can succeed while restore rejects with all original roots still absent, and that exactly two passes fit at the inclusive boundary. The documentation accurately limits restorable payload to at most 2 GiB under this accounting, subject to other bounds, and does not promise every saved snapshot will restore within budget. Later unpredictable I/O/deadline failures may still leave partial inactive roots; no broader atomic-restore guarantee is claimed.

**Restore remains inactive and preserves sealed identity.** A separately supplied manifest digest is required; closed fields, allowed unique category/name inventory and content hashes are validated. Live enablement rejects. Manifest roots must exactly match the configured original locations, and every destination must be absent, including symlinks, with trusted private parents. Restore uses exclusive creation and both writer locks, copies the already-verified files and checks content again. It neither rewrites absolute retained-artifact paths nor invokes a provider/publication effect. Output explicitly requires publication reconciliation. Application readers remain responsible for full schema/record validation on reopen; backup preserves database state rather than migrating it.

**Cross-component recovery is concrete.** The final Qwen test uses the real HTTP executor/decoder with a mock transport and actual deterministic artifacts/SQLite. It retains native V1 and HTTP V2 records, snapshots through a path containing spaces, percent/question/fragment characters and Unicode, moves old roots, restores at the same paths, reopens the records and constructs validated factory publication bundles for both. The standalone WAL test demonstrates that copying the main SQLite file alone misses a committed fixture table while the backup API includes it without side-file dependency. Populated F publication state survives backup/restore and opens through the corrected strict readonly reader without any publication method being called. These are real disposable data-path checks, not real provider/site operations.

**Installer is an inactive, explicitly operational template.** Source inspection confirms fixed local Git argument lists, exact clean control/landing identities, independent no-hardlink clones, a new non-overwritten release name, canonical remotes and default-off generated host config. The script prepares a venv/packages/directories and generates a unit inside the release; it contains no systemctl enable/start/reload, credential provisioning or hosting mutation. Those preparation steps themselves require separately authorized root execution and may install dependencies; this review did not run them. Existing partial releases are preserved. The service template uses the dedicated identity, Unix-host entrypoint, restricted write locations, read-only installed source/config areas, resource limits, no automatic restart and a stop window beyond the host graceful timeout. Its environment-file path is only a future operator input; no file at that path was inspected. `sh -n factory/runtime/install-claw.sh` passed as syntax-only validation.

**Architecture and final assembly remain exact.** G adds backup to the offline rule/group, runtime templates to LOCAL-API ownership and the backup console entry point, reaching 22 classified landing modules. Existing factory/test ownership and network exceptions are not broadened; the unrelated trust-ci resource-path change is ordering only. Current deploy archive membership remains 22 with historical 19/20 layouts retained. Independent byte comparisons against corrected F confirm preservation of provider contracts, landing SQLite cleanup, shared settings/server fixes, strict publication store and their C/D/F regression modules.

An independent full Git tree audit was recomputed directly with `git ls-tree`, using the explicit shared-documentation and old/new change-package dispositions. The union has **2,523 entries** (current 2,426; frozen reference 2,260; initial base 2,136). Product differences from frozen `f31406e970d67f7cd59694da5de88915adb0fa68` are exactly the ten paths listed in `final-product-dispositions.md`, with no additional unclassified product differences or mode/type changes. This is reconstruction/parity evidence; the actual current diff and verification remain review authority.

## Completed verification examined

The fresh `split-g3-full-final.json` reports PASS for this exact route, HEAD and fingerprint. All reported mandatory architecture/drift/diagram, governance, contract/static/security, coverage and source-stability checks pass; core 653, factory-unit 51, PostgreSQL suite 690 run with one skip and two actual restarts, exact-role recovery/reconciliation. Interrupted G2 full verification is not represented as a G3 result.

Independent bounded rerun passed **5 tests in 1.044 seconds**: known second-pass budget rejection/inclusive success, both active writer conflicts/release, committed WAL-only snapshot content, populated publication-intent roundtrip and the final mixed-V1/V2 Qwen mock recovery/publication-bundle test. The other backup/path/tamper/import-isolation tests were inspected. No full suite was repeated. Source status remained clean.

## Limits and handoff

The preserved D P3 remains: malformed SSE object/list values in scalar enum positions can raise TypeError; the durable service still records needs_human/internal_failure and purges input without artifact or authority bypass. This report does not claim universal domain-error classification or infer a Qwen moderation trigger. No new G blocker follows from that existing diagnostic limitation.

PASS is bounded independent local code-review evidence, not external exact-SHA App Trust CI, signed approval or production/merge authority. Cooperative locks do not prove that a raw SQLite client or writer holding a renamed old root has stopped; the documented operator stop boundary remains necessary. No power-loss-at-every-fsync or hostile same-UID filesystem guarantee is asserted. The runbooks correctly retain V2-compatible rollback, absent original destinations, preservation of partial failures and observation-only reconciliation; restoring state does not restore the public pointer. The dedicated host metrics behavior is documented as unavailable/404 rather than Factory metrics. Real hosting facts, credentials, service activation, installer execution, provider/media acceptance and publication/rollback require their own operational authorization and evidence. This reviewer performed no source edits, credential/grant reads, installer execution, operational-state access or external writes.

## SHA-256 inventory of all ten G product/test changes

- `architecture/rules.yaml`: `28d1b6ac60ecfd22db094b800e5be02864e2fc37080edd9fc9c25c7ec76b6a10`
- `architecture/system.yaml`: `7c14e36980642e4694d94d5ed4173960c94964f5457270ec6cbda7d0f09f00ef`
- `factory/pyproject.toml`: `fd4c7c90af68f5644f82453b494edbbc8ba06f31eee606c183069deefa57d82f`
- `factory/runtime/adaptive-l5.service.in`: `5e287944a6e8c58b46a0b119f3064b655df0bc5f4e152712f5a7312455979ebd`
- `factory/runtime/install-claw.sh`: `65074f3807800bed2b34e6c3accf3dddae65b1d9f319d8c3d2a336ce36e93e91`
- `factory/runtime/landing-host.example.json`: `5e7c334ba90c21a578cab19f292c6037d5709f0424554dca67f5bfe0360ea604`
- `factory/src/adaptive_factory/landing_backup.py`: `d3c0a22fc0a84705ff8505b8b2e06d6730a899d24ed90ca553fa405be51f5b99`
- `factory/tests/test_landing_backup.py`: `84183519c4aefa9e4518744d81c30b9dca045c50812956721a3999f55036cbd3`
- `factory/tests/test_landing_live_executors.py`: `2cc7b45945f05a2cc15bf87c8a0462e32e86ba4c51785252a3a9bd7be085a71c`
- `tests/test_landing_architecture_boundaries.py`: `c83af1d6752afb4af07d75427bd60c52db947b44ebe7d6ba22a9a876f310fa48`

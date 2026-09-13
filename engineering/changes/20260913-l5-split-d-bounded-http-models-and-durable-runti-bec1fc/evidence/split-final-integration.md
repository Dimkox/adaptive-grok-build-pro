# Final-source integration map for the seven-PR split

Read-only source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-production`, frozen `f31406e970d67f7cd59694da5de88915adb0fa68`, compared with `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`. Route `8632a3272f03` selects integration_architect for this analysis; root owns routing/delivery and general_implementer remains sole code writer. I read the durable `evidence/continuation-delivery-split.md` and final code. No product files, branches, grants or external services were changed. The seven-unit order remains coherent, subject to actual per-slice fitness and verification.

## Corrections to the preliminary plan

1. Final v2 work includes **a versioned retained-artifact envelope**, not merely evidence union annotations. Retention must emit its evidence version and reject an envelope whose version differs from its nested evidence. All these hunks belong to C.
2. The final Qwen composition test has a cross-feature tail requiring backup, host and publication. D cannot copy the final test file unchanged: defer final lines 339–372 of `factory/tests/test_landing_live_executors.py` to G. Keep lines 268–338 and 373–377 in D. This preserves HTTP sealing, v1/v2 retained-envelope rejection and SQLite reopening in D, and adds full backup/restored-publication validation only once its modules exist.
3. The finalized config seam allows an exact small split: D introduces only `_check_ancestry` and `_private_directory` from `landing_host_config.py`; E adds `LandingHostConfig` and `load_host_config`. D's `landing_server.py` imports only the two private helpers. Do not copy the loader untested into D merely because its eventual module name contains host.
4. Schema-inventory expectations in `factory/tests/test_semantic_bridge.py` and `test_semantic_contracts.py` must accompany C's new schema. They were not named in the preliminary test list.
5. The final `factory/tests/__init__.py` adds delivery and governance import paths for offline operator tests. Its first necessary destination is F, not D. F's test imports adaptive_delivery before importing the wrapper that also sets sys.path.
6. Final `test_landing_architecture_boundaries.py` contains hardcoded future modules and a staged-delivery exception assertion. It must be reconstructed incrementally; copying it whole into A would fail before D/E/F/G exist.

## Exact shared-file sequence

Line numbers below refer to frozen f31406e, not to the intermediate slice files. Named anchors remain authoritative when line numbers shift.

| Shared path | B | C | D | E | F | G |
| --- | --- | --- | --- | --- | --- | --- |
| `factory/src/adaptive_factory/landing_artifact_retention.py` | Replace imported DEPLOY_MEMBERS with deploy_members_for_source at 18; choose members from artifact source SHA/tree at 223; manifest count from self.member_names at 295 | All remaining final diff: union/decoder imports 29–30, field/capture annotations, envelope version dispatch 108–134, version emission 142, exact evidence class/version/disposition validation 175–184 | No further edit needed | — | — | — |
| `factory/src/adaptive_factory/landing_runtime.py` | No change | Import LandingProviderEvidence and builder build argument/isinstance changes near 18, 85, 90 only; retain original compose_landing_live body | Take final compose_landing_live extraction from 217 onward and create_landing_artifact_builder; preserve C union edits | — | — | — |
| `factory/src/adaptive_factory/landing_host_config.py` | Absent | Absent | New file with docstring/future, os/Path/stat, SettingsError, `_check_ancestry` at 62–72 and `_private_directory` at 75–83 | Add dataclass import, strict_json_object, FactorySettings/read_private_file, dataclass 14–18 and load_host_config 21–59; resulting file equals frozen final | — | — |
| `factory/src/adaptive_factory/api.py` | No change | No change | No change: existing general API remains usable | All five final addition hunks: argument 272; validity guard 274–275; readiness 467–468; metrics 476–477; landing-only early return 627–629 | — | — |
| `factory/pyproject.toml` | No change | No change | pypdf dependency and PDF-worker package-data only; co-locate uv.lock | Add adaptive-landing-server script only | No factory console-script hunk | Add adaptive-landing-state script |
| `factory/tests/test_landing_live_executors.py` | Keep existing transport tests, using B sealed_target fixture | Keep existing transport tests; do not import HTTP producer into C | Final file except final 339–372; keep the Qwen test's last live_url/member checks 373–377 | No required edit | No required edit | Insert 339–372; final cross-feature test now has every dependency |
| `factory/tests/test_landing_sqlite_store.py` | Both final source identity changes: renderer constant imports and BASE_SHA/BASE_TREE assignments | Existing SQLite reader tests remain relevant | Add meaningful writer-lock regressions here if needed; there are no new lock tests in the frozen diff of this file itself | Host tests add host-lifetime coverage | — | — |
| `factory/tests/__init__.py` | Preserve base factory/src bootstrap | Preserve | Preserve | Preserve | Take full final diff adding delivery/src and .grok-stack | Preserve |
| `architecture/system.yaml` | Existing source owners suffice | V2 contract object, DOGFOOD public_contracts and schema repository path | DOGFOOD: config helper, HTTP, media, SSE, PDF worker; LOCAL-API: landing_server | LOCAL-API: landing_host, test_landing_host; runtime path if first template introduced | DOGFOOD: publication CLI; staged-delivery request schema path | DOGFOOD: backup; LOCAL-API runtime path if deferred |
| `architecture/rules.yaml` | A's existing-source restrictions | Same | Add only existing D modules to offline rule; host rule initially has landing_server only | Add landing_host to host rule | Add publication CLI offline path; ensure staged-delivery exact urllib.parse exception is active | Add backup offline path |
| `tests/test_landing_architecture_boundaries.py` | A inventory | Same inventory | Add D module names and host group landing_server | Add landing_host | Add publication CLI; update exception expectation if activated here | Add backup |

Do not copy final `architecture/system.yaml` wholesale early: it would declare absent schemas, host, publication, backup and runtime paths. The unrelated sorted trust-ci/resources path movement is canonical-order housekeeping, not a feature prerequisite.

## B: source epoch, whole-file and fixture closure

Take final `landing_renderer.py`, `landing_evaluation.py` and `landing_artifact.py` whole, plus exactly the three retention source-layout hunks above. This includes `ExactGitLandingWorkspace.validate_source()` now; D calls it before acquiring a model credential or sending input. There is no reason to charge the entire renderer a second time in D merely to move that method later.

Take the complete final changes in `factory/tests/test_landing_renderer.py`, `test_landing_artifact.py`, `test_landing_api.py`, `test_landing_live.py` and `test_landing_sqlite_store.py`. These are source-epoch changes, not dedicated-host API tests. The sealed_target fixture adds analytics, source-owned internal docs and a patch of retention.deploy_members_for_source for its synthetic Git identity. That patch requires B's retention import change. Production's supported-epoch lookup remains strict; do not replace it with the fixture's patch behavior.

B must keep v1 evidence/retention semantics until C. `ASSETS.md` and `SERVER-SETUP.md` are source fixture members, not deploy inventory additions. The final artifact module preserves that distinction.

## C: complete v1/v2 readers and independent proof

Take final `landing_contracts.py`, `landing_provider.py`, `landing_service.py`, new `factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json`, and the C shared-file hunks above. There is **no final change to the v1 JSON schema**; preserve its exact frozen bytes. Python validation additionally rejects non-integer schema versions and maintains the existing v1 digest domain while adding an independent v2 digest domain.

Take final `factory/tests/test_landing_contracts.py`, `test_semantic_bridge.py` and `test_semantic_contracts.py`. These have no new HTTP dependency. The contract tests check pinned v1 bytes/digest, v2 domain identity, and closed dispatch for unsupported versions.

A reader-only C still needs its own retained-artifact/SQLite roundtrip evidence: the frozen monolith puts that proof inside D's HTTP test. Reuse `factory/tests/test_landing_runtime.py`'s existing `_bound_output`, BoundProvider, CoordinatedLandingArtifactBuilder and real temporary SQLite fixture. Create a synthetic V2 variant by converting existing evidence facts (remove digest, set schema_version=2/disposition=normalized), rather than calling landing_http or the future create_landing_artifact_builder helper. Exercise both evidence versions through the existing direct builder/store, compare the reloaded v1 envelope bytes and reject crossed envelope/nested versions and version 3. This is a narrow needed test adaptation for the reader-first delivery order; it does not require changing reader behavior or adding a production producer in C. Its touched-file budget must be measured.

Keep C's reader test when D/G later add broader integration tests. Do not claim C's independent verification from a passing test that was only runnable against the future monolith.

## D: whole-file closure and transport tests

Take final `landing_http.py`, `landing_live_executors.py`, `landing_media.py`, `landing_sse.py`, `resources/landing_pdf_worker.py`, `landing_normalizer.py`, `landing_intake.py`, `landing_sqlite_store.py`, `landing_server.py`, `settings.py`, existing `server.py`, plus the D shared hunks. The config helper contains only its two filesystem functions at this point.

The dependencies are real: HTTP normalization calls the shared draft/text decoder; media uses the packaged PDF worker/pypdf; live composition uses SQLite and the extracted artifact builder; existing server uses compose_server_landing; settings supplies explicit live enablement/durable paths; server composition calls B's source guard before credentials and takes the writer lock before blob-store recovery. Preserve final Qwen region/key-file validation, surrogate rejection, DOCX duplicate/casefold rejection, bounded SSE, PDF process cleanup and default-off behavior as one runnable transport slice.

Take final `test_landing_media.py`, `test_landing_sse.py`, `test_landing_normalizer.py`, `test_server.py`, and the D selection of test_landing_live_executors above. Its 268–338 segment already proves normalized v2 production, independent native v1 retention, crossed-version rejection, close/reopen and byte-stable legacy reloading; it uses only B/C/D modules. Its 339–372 segment is the sole future-module dependency found in that file and must wait for G.

The final host test file contains D-owned composition guarantees at 265–316: source validation precedes credential acquisition; a competing SQLite writer blocks acquisition; failed composition releases ownership. Because that file imports landing_host at module top and uses its loader fixture, it cannot simply be copied into D. Adapt those assertions into a direct composition fixture under the existing server/store tests: construct FactorySettings directly with sibling 0700 temp state/blobs/scratch/output directories, no PostgreSQL connection, and mock source guard/provider function before any network call. Also prove a second real SQLite owner is refused and ownership is reusable after close/startup failure. The entire host test file remains an additional E delivery. This avoids shipping D's security/lifecycle guarantee with tests delayed until E.

Use existing NODE-LIVE ownership for landing_live_executors only. HttpLandingProfile and HTTP response DTOs in landing_http do not directly perform network I/O and retain offline/httpx-forbidden ownership.

## E: loader, dedicated host and all host tests

Complete landing_host_config with the loader/dataclass hunks, then take final landing_host.py, api.py changes, `factory/tests/test_landing_host.py` and the host console entrypoint. No publication implementation is needed to create/validate the host's separate publication_state directory. Its name is not a Python dependency on F.

The final host tests all become runnable here: closed config, every root pair, double-slash aliases, secrets outside data roots, no provider read while default-off, credential ordering, lock/lifespan ownership, listener identity and nested cleanup. The fixture's re-export uses `landing_host.load_host_config`; the actual loader globals now reside in landing_host_config. Preserve call-site patch names as the final code does. Tests that target moved inner globals must target their defining module.

Runtime JSON example can be introduced here with its exact owner. Defer the complete installer/systemd operational documentation to G for one coherent assembled install description.

## F: publication and governance bridge are indivisible

Take final delivery `landing_filesystem.py`, `landing_publication.py`, `landing_publication_contracts.py`, request v1 schema, final factory landing_publication_cli.py, scripts/grok_landing_publish.py, final factory/tests/test_landing_publication_cli.py and tests/__init__.py bootstrap change. The publication test uses candidate_fixture from B's artifact tests and sibling delivery/governance packages; it does not require backup or dedicated host.

Retain the final external-write scope correction and exact action/resource singleton, route/change/current Git identity, unique grant match and bounded private grant read in the governance script. Product main requires injected callable authority for apply before config/state access. The supported wrapper injects the concrete authorizer. Copying only the product CLI or only the script yields an incomplete authorized operator path.

F also carries final publication // path fixes, exact GitHub remote validation, SQLite Path.as_uri special-character handling and no-create readonly regressions. Preserve URL parsing with the narrowly allowed urllib.parse module; no broader urllib/network allowance. The factory CLI has no adaptive_grok imports in the final source.

## G: actual backup dependencies and the final Qwen tail

Take final landing_backup.py and test_landing_backup.py, backup console script, full runtime installer/templates and coordinated operational docs. The backup module directly imports landing_host_config; its test inherits HostFixture from E's test_landing_host.py. Its snapshot and restore use F's publication filesystem locks, and snapshot imports F's publication database APPLICATION_ID even if that database is absent. Therefore E and F are prerequisites for copying these exact final files.

Restore final 339–372 in the Qwen composition test now. It snapshots both versions, renames old inactive roots, restores them, opens SQLite and constructs publication bundles for both restored jobs, including a snapshot path with spaces/%/?/#/non-ASCII characters. This is useful final integration evidence; it must not be removed merely to keep D independently runnable. The existing host re-export for LandingHostConfig is available in E; importing the defining offline module instead would be a small optional test cleanup, not a dependency repair required for G.

## A inventory details that affect every later slice

A can activate the final staged-delivery exact-module exception together with its schema/evaluator support and synthetic tests; then the final `test_uri_exception_is_declared_only_for_staged_delivery` assertion remains valid from A onward. Alternatively defer both model entry and assertion to F. Do not activate one without the other.

Initialize the inventory with only actual base landing modules, and expand it per the table. The final overlap regression currently uses landing_backup.py as its duplicated member; before G use an already-present offline member such as landing_artifact.py, otherwise it fails for incompleteness instead of exercising overlap. The host group/rule starts with landing_server in D and gains landing_host in E; do not introduce empty source_prefixes if the rule schema requires a nonempty list. All rule tightening for already-present paths must actually pass against A's base implementation.

Completeness and direct-import mutation tests remain mandatory per actual tree. They must continue rejecting unclassified empty modules and offline httpx/socket/urllib.request/psycopg/trust imports; stage-aware expectations are not a waiver for missing classification.

## Reconstruction and acceptance approach

Use f31406e as the immutable source of final content. For single-unit files, copy the frozen content into that unit; for the shared paths above, construct explicit predecessor-to-next patches keyed by named symbols/hunks. Keep a durable path/hunk manifest per slice so every final product delta has exactly one introduction and necessary later completion. Do not cherry-pick the monolith or overwrite a shared file with final content before all its dependencies exist.

After each slice, inspect imports and test collection, run the focused regressions needed for that actual slice and the prescribed full `python3 scripts/grok_verify.py --mode pr`. Measure all actual budgets, including newly adapted reader/composition tests, whole touched shared files and governance checks. Obtain per-slice fingerprint-bound reviews/receipts against its genuine base. The earlier source-node estimates do not prove a pass and must not be used to change any rule budget or arbitrarily substitute a base.

After G, compare product source/schema/package/runtime content with f31406e and explicitly account for every difference. Necessary extra independent reader/composition tests may strengthen the delivered tree without changing product behavior; retain their evidence and budget impact. Verify the final assembled tree again and let root handle the actual PR topology, rebase/evidence freshness and external exact-SHA Trust CI checks. No local or earlier monolith receipt substitutes those gates.

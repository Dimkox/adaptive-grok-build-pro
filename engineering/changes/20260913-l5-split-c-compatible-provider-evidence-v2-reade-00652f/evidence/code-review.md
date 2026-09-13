# Independent code review — split C

Verdict: PASS for the bounded compatible provider-evidence readers. No blocking correctness or security finding identified in the actual diff and surrounding implementation.

## Reviewed identity

- Route: `00652f60f78c`; change: `20260913-l5-split-c-compatible-provider-evidence-v2-reade-00652f`.
- Immutable source HEAD: `9ce156e0128b4f18b3fccfeca9a8edc7175da090`.
- Genuine route predecessor: `c46f14f6a39ca8dc778f8a179ab4f61cdfe13599`. The actual PR stacks on B; subsequent documentation corrections were merged from the predecessor branch without changing the original route base.
- Verified tree fingerprint: `b08cf1e0ea54ad38e3a8d25895603670b460a01e3b65428365ff51751d8bffd3`.
- Independent reviewer: `code_reviewer`; application write owner: `general_implementer`.

Read the active route, reviewer role and package requirements/architecture/test plan; inspected the actual source, schema, catalog and test diff below, surrounding retained-artifact integrity checks, provider outcome validation, runtime construction and SQLite serialization/reload behavior. No later HTTP producer or backup source was used to infer this unit's behavior.

## Findings and reasoning

V1 remains a distinct published representation. Its schema is byte-for-byte equal to initial main `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`, independently compared with `git show`; SHA-256 is `67ab4380cf6f5a465c0aa6e60223e77beba28f785af6088867a3acbc33ec8afd`. Its digest contract domain and successful `fixture_ready` disposition remain unchanged. The golden V1 test fixes both the known evidence digest and original schema bytes, rather than generating expected values from the new implementation.

V2 is a separate sibling record with schema version 2, a distinct `/v2` digest domain, and `normalized` as its successful disposition. Closed-field validation, canonicalization, timestamp ordering, identity/usage bounds and supplied-digest validation are shared without making V2 an instance of V1. The dispatch function requires an actual integer version 1 or 2, rejecting booleans and unknown versions. V1 and V2 outcome validation preserve their respective success dispositions and require the appropriate runtime class/version pair.

Retained envelopes carry the nested provider version, and decoding rejects crossed envelope/evidence versions before artifact construction. Both versions still pass the same source/input/profile/attempt/evaluation bindings, exact source-epoch member selection, canonical manifest and archive integrity checks. There is no permissive fallback from malformed V2 to V1 and no implicit rewrite on read. The schema and architecture/semantic catalogs explicitly register V2 without mutating the V1 contract.

The new mixed-evidence test is meaningful persistence coverage: it constructs actual coordinated artifacts through the deterministic renderer/evaluator/packager, submits one V1 and one V2 job to a real private SQLite store, closes and reopens it, validates both artifacts, compares raw persisted V1 JSON before and after, and checks that provider calls were not replayed. It also exercises unknown/boolean/crossed envelope versions and stale evidence digests, then writes a tampered retained row in its isolated test database and confirms that reopening rejects it while V1 remains readable. The V2 provider in that test is a local deterministic adapter; the test has no dependency on the later HTTP runtime or backup module.

## Verification examined

The completed `split-c-full-final.json` reports PASS for this exact route, HEAD and fingerprint. Every reported mandatory check passes, including architecture/governance, contracts/static/security checks, 653 core tests, coverage, factory tests, PostgreSQL verification with two actual restarts and source stability. The actual mixed-SQLite test and contract regression assertions were inspected rather than accepting historical proposed test counts as results. No broad suite was rerun during review. A bounded independent check additionally verified original V1 schema byte equality and that both schema adapter-version patterns accept `1.0.0` while rejecting malformed separators.

## Limits

This unit provides readers and acceptance plumbing; it does not claim a network producer, publication workflow or backup implementation. Old runtimes cannot read new V2 retained records, so rollback after V2 writes requires retaining the compatible reader or restoring a pre-V2 snapshot; the package documents that boundary. PASS is independent local review evidence, not external exact-SHA Trust CI approval or merge authority. No source edits, credentials, operational grants or external writes were performed.

## SHA-256 of inspected product/test delta

- `architecture/system.yaml`: `86b45dc1cacf56dae1dd4b72d972296dec3e14c9b50640c1e3338490c7ae696f`
- `factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json`: `888ddf6ee0042cb332ae17904d1c0f7269894e863ee37ba3b7a950e463bc9eeb`
- `factory/src/adaptive_factory/landing_artifact_retention.py`: `c2016e054010a2f26d34b25b97615eb4d13964986a8deade58a0c42efbc484f0`
- `factory/src/adaptive_factory/landing_contracts.py`: `e69b8f754570a62bc168e0c73069b398e6166699127386c8ba69e4c8753cc6d8`
- `factory/src/adaptive_factory/landing_provider.py`: `031fd7cd31be8bbf7a1b98e022a6592818a64d5f05da0da80c182c6b17339cb6`
- `factory/src/adaptive_factory/landing_runtime.py`: `d1805ac32f7e15ef35ddabdaa8d87f2d234b95fd39feb89093e52e8236395461`
- `factory/src/adaptive_factory/landing_service.py`: `b6d6ca442aed9f01f541cfd2c44e9632c30b05e34df4bf066bd7819b3d688b3b`
- `factory/tests/test_landing_contracts.py`: `98927025419de33ba3fa7d2c2acac59b16982c4d72cea45f08f85d9466abd302`
- `factory/tests/test_landing_runtime.py`: `246dca28b92a1f8b313f3620e09c3d30f66f8b6e92724eb0c265f3ddf4867643`
- `factory/tests/test_semantic_bridge.py`: `0389767fe99830b448bad57b5f59e786d4814b063fe0db367cf9d3305b8f7d98`
- `factory/tests/test_semantic_contracts.py`: `5d38739bfaa1c9709fa11ddd6c85b2ca80967e48a57576b1e5ca589a90a1f1ea`
- `tests/test_architecture_fitness.py`: `be87cf5b1ac76ff115f5ecbac7df5337b03ec5e1f87b6957341fccf299480146`
- `tests/test_architecture_model.py`: `aba093773e2974fdc84ca1ed604d38ac545689e793b16d7daaec1d754b3552ea`

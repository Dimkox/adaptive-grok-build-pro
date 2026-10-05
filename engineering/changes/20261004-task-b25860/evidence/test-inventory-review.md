# Independent test review — inventory-binding repair

PASS for the bounded inventory-only repair. All three formerly failing named controls pass fresh, and four independent actual-schema-file mutants are killed. No finding remains in this delta. This is not a full-verification PASS: previous full gate at b39c36ec984423e5201abf4f91bd3ee7202c23de failed and remains historical; current source requires fresh final full verification and App-owned exact-head Trust CI with no reused skips.

Route b258608f2ced/change20261004-task-b25860; agreedbase2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Candidate <repository-root>/.review-scratch/m8-one-task-autonomy. Before/after review HEAD88ff98b3d77f793a3ab43633b18e577b13e47eaf, fingerprint73d8352bd6d6d726bc14a952a337e7788b44c14903f2c314b02881f2497bfbf6, clean gitstatus. Earlier complete initial and authority follow-up reports retain their original1861/822identities; no earlier observation is relabelled fresh.

reviewed-tree-modified: no

## Resources, isolation and inspected change

Startup2026-10-05T01:05:19Z CPU/cgroup/ancestor quota measurement privately recorded in capacity.md before source/route inspection:14physical/28online logical0-27, defaultprocess22affinity0,1,8-27; actual root-mounted cgroup2 /user.slice/user-1000.slice/session-2050.scope, inheritedcpuset0-27, session/user-1000/user.slice quota max100000, root cpu.max absent, no finite ancestor quota observed. Bounded child-only widening0-27 verifies28 with same membership/quota; controller affinity unchanged. Allocation oneprocess0-3<=4CPUs. Trusted owned nonsticky parent .review-scratch and private <repository-root>/.review-scratch/test-review-m8c-cBuaRC are0700.

Fresh private snapshot <repository-root>/.review-scratch/test-review-m8c-cBuaRC/snapshot created with `GIT_OPTIONAL_LOCKS=0 git clone --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/test-review-m8c-cBuaRC/snapshot`. Exact88ffHEAD/73d8fingerprint/cleanstatus matched before probes and after restoration. Candidate reads used GIT_OPTIONAL_LOCKS=0/PYTHONDONTWRITEBYTECODE=1. All four schema-byte mutations/restorations used apply_patch only in private snapshot; the newly created unknown-schema mutant was removed from that snapshot after its test. Candidate files/runtime/index were never edited, generated or restored.

Inspected fullb39..88ff6-file diff and private writer inventory report. Product changes are only three binding tests; other files are decision/mistake lessons and explicit repair phase state. Production runtime, schema bytes, policy and runner are unchanged. Both semantic inventories add exactly owner-autonomy.v1.schema.json while retaining explicit complete filename sets. New checks require2020-12dialect, exactly policy/case/activation defs and matching three oneOfrefs, each variantadditionalPropertiesFalse, required/properties set equality, schema_versionconst1. Landing historical view excludes only the exact added owner path, preserves original23count and literal98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc digest, asserts one exact currentminimum1line and parsedfloor1, restores only that line's1→30 in memory for historical comparison. Every other predecessor byte remains in original digest. No historical digest rebaseline or broad schema exclusion.

## Fresh controls and mutation evidence

All commands run in the private snapshot. Exact prefix E: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3`.

Command C3:

`E -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`

Claims: exact successor admission and variant shape/version binding; historical predecessor contract/migration/showcase/published record pins preserved through the explicitly approved floor comparison. Before mutation C3 exit0,3tests,0.356s,OK; bridge's actual schema-validation subprocess executed. Restoration C3 exit0,3tests,0.413s,OK. No full factory/owner/whole-branch suite was repeated.

Command C2:

`E -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields`

M1 unknown-schema admission KILLED. Added actual private `factory/contracts/jsonschema/unapproved-successor.v1.schema.json` containing{}. C2 exit1,2tests,0.001s,2failures identifying unapproved-successor.v1.schema.json outside each exact expectedset. This proves inventory remains closed after admitting only owner successor. Removed private mutant via apply_patch.

M2 owner closure KILLED. Actual owner schema policyvariant additionalPropertiesFalse→True. C2 exit1,2tests,0.455s,2failures at owner_variantpolicy `True is not False`. Restored afterward.

M3 owner version KILLED. Actual owner schema policyvariant schema_versionconst1→2. C2 exit1,2tests,0.370s,2failures{'const':2}!={'const':1}. Restored afterward. Closure/version tested independently, so one guard cannot mask the other.

M4 unauthorized floor KILLED. Actual earned-autonomy minimum_human_acceptances minimum1→2. Command `E -m unittest factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen`:exit1,1test,0.005s,1failure exactapprovedlineoccurrence0!=1. Historical normalization cannot silently admit an alternate current minimum. Restored afterward.

Scratch and candidate post-review inventories clean; exactsource identities unchanged. No survived or inconclusive mutant in this bounded set. Code reviewer independently owns the other old-contract-byte mutation; its result is not duplicated or claimed here. Report contains no blanket mutation-score threshold.

## Unexecuted limits and handoff

No new fullverifier/fullPostgreSQL/coverage/fullCore/fullfactory/oldowner/wholebranchsuite; no runner optimization or verification-scope change. Prior failedb39gate components remain historical at that exact identity and grant no skip or fresh completion. No independent live/provider/deployment/SHAP/other-repository work, secrets, childagents or external writes; another-repository request is outside this routed scope. Owner policy/runtime authority semantics were not re-reviewed in this test-only delta; earlier exact reports retain that evidence. Human approvals/externaltrust/publication remain separate. All observations stopped; coordinator persists complete reports after both selected reviewers stop, freezes new source, then runs fresh full gate/App check.

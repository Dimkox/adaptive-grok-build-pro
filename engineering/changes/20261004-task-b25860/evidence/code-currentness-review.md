# Independent currentness / wire-compatibility follow-up — PASS

Route b258608f2ced; change20261004-task-b25860. Read the complete private implementation report `.superpowers/sdd/tasks/task-1-currentness-report.md`, actual21-file repair `f8393ea5ba3bd8d014e46fa947d20fd78362247d..ccbbccc318c141b1aada9b61050cbceb7c56a4ef`, relevant surrounding source and exact-V1 M9 consumer. This bounded follow-up covers the confirmed executable-inventory, current-route, same-version-wire and isolated-import defects; it does not repeat or reissue prior whole-branch reports.

## Source and isolation

Candidate `<repository-root>/.review-scratch/m8-one-task-autonomy`; agreed PR base `2a8e3839a469b3e05da167e9d8a807bf18e6adbf`.

Before and after HEAD: `ccbbccc318c141b1aada9b61050cbceb7c56a4ef`.

Before and after fingerprint: `4a4c14a0a64bbcb87a33d6ebe399108fd82faf3582f39d51352662046f3e9b0f`.

Before/after `git status --porcelain=v1`: empty. All candidate commands set `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`; no source/runtime/index/HEAD/branch or bytecode writes there.

Fresh exact private clone `<repository-root>/.review-scratch/code-currentness-12AiHe/repo`, created with `git clone --quiet --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/code-currentness-12AiHe/repo`. Its HEAD/fingerprint matched clean candidate; no dirty-source overlay required. Trusted parent `.review-scratch` and reviewer directory ownedpall/mode0700/non-sticky. All source mutants were applied and restored only in the private clone via apply_patch; final scratch `git diff --exit-code` exited0. Synthetic CLI fixtures were created only by tests within their private temporary directories.

reviewed-tree-modified: no

Startup resource discovery recorded privately before source/route reads at2026-10-05T02:01:37Z:14physical/28online logical CPUs0-27, defaultprocess22/affinity0,1,8-27; actualcgroup2 session2050/user1000/user.slice ancestry unlimitedcpu.max and inheritedcpuset0-27. Child-only widening verified28 with unchanged membership/bounds. Allocation4CPUs, one test process at a time. Final candidate observation02:04:11Z:154seconds, within180second bound. No agents/full verifier/full factory replay.

## Findings and assessment

No critical, important or minor finding in this bounded repair review. Previously confirmed gaps are resolved within stated limits.

Source currentness now hashes actual bytes and modes from complete cached/nonignored-untracked Git enumeration, rather than selected directories or status flags. Root tests/scripts/hooks and unknown modules are included; assume-unchanged no longer hides a changed file. Inventory/count/per-file/total bounds are explicit; reads use no-follow descriptor traversal, regular-file/type/size/metadata checks, and head/inventory are rechecked. Recognized credential paths refuse before open. Ignored runtime/generated artifacts stay outside the declared Git-visible source binding, as documented; the code does not claim an atomic snapshot against a malicious same-user writer.

Route binding is now derived from validated actual route identity/task/intent/risk/domains/selected agents/profiles/gates/evidence, with closed supported risk/domain handling and selected-agent consistency. Missing/malformed/high/security/production/required-gate cases fail closed; compatible medium/API/base+contracts work remains limited to local_read/local_test. Sorted semantic arrays and omitted compatible phase/timestamp fields avoid irrelevant invalidation. Every decision still carries L1-or-L0, ceilingL2 and externalfalse.

Legacy V1 constructor/parser minimum30 and original schema bytes are restored. Additive CohortEvidenceV2 has explicit schema_version2, minimum1 and separate digest domain; unchanged nested tuple/task/M7 and output profile/recommendation contracts remain V1. The evaluator accepts exactly V1/V2 classes, not arbitrary derived types. M9's existing `type(self.cohort) is CohortEvidenceV1` plus reparsing continues to reject V2 on objects and wire. Literal historical aggregate no longer normalizes floor bytes and excludes only the two named successor schemas. No M9 production module or deployed Trust CI behavior changed.

The isolated root state test imports its own repository factory source explicitly, removing ambient collection dependency. Current README/state/acceptance criteria describe actual route requirements, complete Git-visible binding, version split and rollback. Architecture changes add only the new contract/path; published2.1.1 and Liqvera evidence remain separate from fresh completion.

## Executed controls

Environment for scratch commands: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`. Working directory is private clone above. No installed source was used as a substitute for candidate.

1. Exact command:

```bash
PYTHONPATH=factory/src:delivery/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_source_reader_bounds_links_and_credentials_fail_closed factory.tests.test_autonomy.OneAcceptanceFloorTests factory.tests.test_autonomy_schema.AutonomySchemaTests.test_v2_changes_only_cohort_wire_and_one_case_floor
```

Observed exit0, Ran6tests in15.775s, OK. These exercise actual separate-process CLI root tracked mutations, hidden assume-unchanged bytes, unknown untracked source, ignored generated/runtime fixture, unsafe source link; missing/malformed/changed route and stable equivalent route; oversized/path-traversal/no-follow reader refusal and synthetic credential-name open interception; legacyV1 minimum/version refusal, explicitV2 minimum1/digest/blocked-M7 behavior, and nested-schema equivalence. Credential probes mocked open before any attempted read; no real credential bytes were read.

2. `PYTHONPATH=factory/src:delivery/src:.:.grok-stack taskset -c 0-3 python3 -m unittest delivery.tests.test_m8_boundary.M8BoundaryTests.test_legacy_handoff_rejects_new_v2_cohort_without_widening_m9` — exit0,1test0.161s, OK. Both typed V2 and serialized V2 cannot enter exact-V1 M9 handoff.

3. `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 -I -m unittest discover -s tests -p test_project_state.py` — exit0,20tests0.188s, OK. Reproduces the isolated App import mode without running full collection or installing factory.

4. Independent chmod-only source-currentness control:

```bash
PYTHONPATH=factory/src:. taskset -c 0-3 python3 -c 'from factory.tests.test_owner_autonomy import OwnerAutonomyTests; t=OwnerAutonomyTests(); t.setUp()
try:
 root,run=t.cli_checkout(); assert run("activate")[0]==0; source=root/"tests/test_structure.py"; before=source.stat().st_mode; source.chmod(before ^ 0o100); code,decision=run("admit","--action","local_test"); print("mode mutation:",code,decision); assert code==2
finally: t.doCleanups()'
```

Observed exit0 for the assertion harness; actual CLI admission exit2, allowedfalse/L0, reasonbinding_mismatch, ceilingL2/externalfalse. Outcome: mode-change input mutant killed.

5. `git rev-parse HEAD:factory/contracts/jsonschema/earned-autonomy.v1.schema.json 2a8e3839a469b3e05da167e9d8a807bf18e6adbf:factory/contracts/jsonschema/earned-autonomy.v1.schema.json` — identical blobs `dc153e0f0199e6e025769cbaeceea6b8086cc7c4`. This is exact restored legacy schema-byte evidence.

## Independent implementation mutants

Applied sequentially with apply_patch only in private clone; controls use the same environment and taskset0-3.

| Claim / mutant | Exact test command suffix after `PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest` | Observed result | Outcome |
|---|---|---|---|
| Replace returned `digest(profile)` with `digest({"static": True})` while keeping route validation | `factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_profile_requires_actual_compatible_route_and_stable_semantics` | exit1;1test1.761s;3failures for route_id, analysis_agents and task changes: admission0 rather than2 | killed |
| Restore profile; omit all `tests/` paths from inventory comprehension | `factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_currentness_includes_root_tests_scripts_hooks_and_unknown_sources` | exit1;1test1.884s; root tests/test_structure.py change admission0 rather than2 | killed |

Restored full current implementation; scratch diff empty. No surviving/inconclusive mutant among these targeted probes, no blanket score claim. Prior findings now have tests that fail under their corresponding weakened implementation; synthetic changed inputs are test evidence, never factual production telemetry.

## Identity commands and limitations

Candidate before/after: `git rev-parse HEAD`; `git status --porcelain=v1`; `PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'` returned identical identities above. `git diff f8393ea5ba3bd8d014e46fa947d20fd78362247d..HEAD --check` exited0. No more candidate observations after02:04:11Z.

Unexecuted/declined-to-judge:

- Full verifier, complete factory/PostgreSQL suite, coverage, App qualification, merge, release packaging/publication and actual final candidate activation remain controller-owned; this report does not reuse prior PASS/FAIL identities as fresh qualification.
- Whole-repository atomicity against hostile concurrent same-user writers, arbitrary unknown secret filename detection, deep malformed JSON exhaustion, every filesystem/platform combination and every inventory-bound edge were not proven. Recognized credential-name refusal and bounded/no-follow reads were checked; no blanket secret-discovery or OS-isolation claim.
- Ignored executables are explicitly outside Git-visible binding; this is a local bounded admission decision, not an arbitrary-command executor or a sandbox allowing ignored payloads to execute.
- Unknown-schema/frozen-history mutation coverage remains in prior exact-head reports and the independent test reviewer's relevant follow-up; those old results are not relabeled fresh here.
- Earlier whole-branch1861 and later repair88ff/f839 triage reports remain historical at their original identities. This report evaluates only the21-file current repair and listed probes.

PASS as independent bounded code/spec/security follow-up. Coordinator must persist complete reports, freeze, and obtain fresh qualifying local and external exact-head evidence before delivery.

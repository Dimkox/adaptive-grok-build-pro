# Independent inventory-only code/security/spec follow-up — PASS

Route b258608f2ced; change20261004-task-b25860. Scope exactly `b39c36ec984423e5201abf4f91bd3ee7202c23de..88ff98b3d77f793a3ab43633b18e577b13e47eaf`: three test modules, short decisions/mistakes entries and workflow phase history. Read complete private writer `.superpowers/sdd/tasks/task-1-inventory-report.md`, actual commit diff and surrounding inventory/aggregate implementations. This is not a whole-branch repeat or a new full verification claim.

## Identity and isolation

Candidate `<repository-root>/.review-scratch/m8-one-task-autonomy`; agreed PR base remains `2a8e3839a469b3e05da167e9d8a807bf18e6adbf`.

Before and after candidate HEAD: `88ff98b3d77f793a3ab43633b18e577b13e47eaf`.

Before and after fingerprint: `73d8352bd6d6d726bc14a952a337e7788b44c14903f2c314b02881f2497bfbf6`.

Before/after `git status --porcelain=v1`: empty. Candidate commands used `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`; no index/runtime/source/HEAD/branch/bytecode writes.

Fresh exact private scratch `<repository-root>/.review-scratch/code-inventory-KftwHp/repo` created using `git clone --quiet --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/code-inventory-KftwHp/repo`. Clean source required no dirty overlay; cloned HEAD and fingerprint matched candidate. Parent `.review-scratch` and reviewer directory ownedpall/mode0700/non-sticky. Mutant was written/restored only in this clone via apply_patch; final scratch `git diff --exit-code` exited0.

reviewed-tree-modified: no

Startup snapshot2026-10-05T01:05:05Z recorded privately in sibling `capacity.md` before candidate/route reads. lscpu/nproc/affinity/cgroup/mount and all actual ancestor quotas observed14physical/28online logical CPUs, default22/affinity0,1,8-27, cgroup2session2050 under user1000/user.slice with inheritedcpuset0-27 and no finite ancestorquota. Child-only widening verified28 with same membership/bounds. Tests used one process at a time on0-3; no agents/heavy full gate.

## Findings and reasoning

No critical, important or minor finding within this delta.

Both exact schema filename sets admit only the newly approved owner-autonomy.v1.schema.json in addition to their previous inventory. The new checks assert exact dialect, exact policy/case/activation definitions and oneOf references, closed variants, required/property equality and schema_version const1. They retain existing version/bridge checks. No generic unknown-schema exemption was introduced.

The historical aggregate excludes only `factory/contracts/jsonschema/owner-autonomy.v1.schema.json`, rather than all similarly named or future schemas. It retains literal23-file count and original `98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc` digest. The earned-autonomy historical view is enabled only for that predecessor aggregate and exact earned-autonomy path. It requires exactly one occurrence of the full expected floor1 line and independently requires parsed cohort_evidence.minimum_human_acceptances.minimum==1. It replaces exactly that one line with its historical30 form in memory, then hashes all bytes normally. Actual base-to-current schema diff confirms this precise one-line30→1 change; unrelated bytes, whitespace and filenames remain bound. The test explicitly does not claim current schema bytes equal historical bytes.

Migration001–018, showcase and publishedv2.0.13 literals are unchanged. No production schema/module, policy, runner, scope selector, server/deployment or App trust change exists in this repair. The reported P0 in another unidentified repository confers no permission for changes here. Workflow phases accurately identify repair and pending fresh gates; a former full FAIL is not converted into PASS.

## Executed claim → command → result

Environment for every command: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`; working directory private clone unless stated otherwise.

1. Three exact repaired bindings:

```bash
PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_semantic_contracts.SemanticContractTests.test_public_schemas_are_closed_bounded_and_have_exact_versions factory.tests.test_semantic_bridge.SemanticBridgeTests.test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen
```

Observed exit0, Ran3tests in0.438s, OK. This includes existing semantic bridge jsonschema subprocess validation. No installation/new dependency performed.

2. Historical unrelated-byte mutant: private earned-autonomy schema `"maximum_security_failures": {"const": 0}` changed toconst1, leaving the approved floor1 line untouched. Command:

```bash
PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_release_record_are_frozen
```

Observed exit1; Ran1test in0.007s, FAILED(failures=1). Expected tuple23/98818e23... differed from23/762539cce0c20b9448d23c1481aaec9d4999facc357ddb58cc8931a5de74ec1b. Outcome: killed. Thus the normalization does not conceal this unrelated security-contract change. Restored original const0 via apply_patch, then `git diff --exit-code` exited0. No surviving/inconclusive mutant in this bounded reviewer probe; no blanket mutation-score claim.

3. Candidate read-only `git diff 2a8e3839a469b3e05da167e9d8a807bf18e6adbf..HEAD -- factory/contracts/jsonschema/earned-autonomy.v1.schema.json` confirmed exactly the approved one-line threshold edit. `git diff b39c36ec984423e5201abf4f91bd3ee7202c23de..HEAD --check` exited0. Before/after `git rev-parse HEAD`, `git status --porcelain=v1`, and `PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'` gave identical candidate identities recorded above.

## Unexecuted claims and limits

- Unknown-schema, variant-shape and floor mutants are assigned to independent test reviewer, not duplicated here. Their assertions were inspected statically; no execution result is claimed for them in this report.
- No full suite, coverage, PostgreSQL, external App check, packaging, release, merge, network/provider operation or deployed mutation performed. Fresh complete final gate on report-containing current HEAD remains coordinator-owned.
- The prior full gate atb39c36ec was reported FAIL; any successful component timings remain historical at that original identity and grant no skip/current completion claim. This report claims only the three named controls and one mutant above.
- Original whole-branch code review at1861e28 and earlier bounded repair review at822a302 remain historical with their original identities. They are not represented as freshly rerun at88ff98b3.
- This probe demonstrates one unrelated-byte guard; it does not claim exhaustive mutation coverage, OS-enforced reviewer isolation or external merge authority.

Assessment: PASS for the exact inventory-only repair. Stop candidate observations and return complete report for coordinator persistence before fresh full local/external gates.

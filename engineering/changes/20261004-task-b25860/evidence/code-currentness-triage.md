# Independent bounded triage — two findings confirmed with qualifications

Routeb258608f2ced; candidateHEAD `f8393ea5ba3bd8d014e46fa947d20fd78362247d`; fingerprint `8dea75f544f20a45fc306af003b46019a90aa28e576116e8b8466978396827b9`; agreed base `2a8e3839a469b3e05da167e9d8a807bf18e6adbf`. This is diagnosis of external review comments about cohort wire identity and hardcoded profile. No repair, merge, external message/write or complete-suite execution authorized or performed. Existing full local PASS is historical evidence on this source; this triage does not claim it caught these gaps.

Candidate `<repository-root>/.review-scratch/m8-one-task-autonomy`; before/after HEAD/fingerprint exactly those above, `git status --porcelain=v1` empty both times. All candidate reads used `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`.

Private scratch `<repository-root>/.review-scratch/code-triage-aerMFb/repo`, cloned using `git clone --quiet --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/code-triage-aerMFb/repo`; scratch HEAD/fingerprint matched candidate, clean source. Parent/reviewer directories trustedpall/mode0700/non-sticky. Scratch origin locally set to canonical GitHub URL solely for offline context validation. Only scratch ignored runtime was generated/mutated. Startup was measured and recorded privately before inspection at2026-10-05T01:31:50Z:14physical/28logical online, default22affinity0,1,8-27, actualsession2050 cgroup2 and ancestors unlimitedquota/cpuset0-27; child-only widening verified28, allocation4/one process. Bounded observations completed within180seconds; no child agents/full suites.

reviewed-tree-modified: no

## Finding1: v1 widened producer domain is indistinguishable to older readers

`factory/src/adaptive_factory/autonomy.py:333` keeps CohortEvidenceV1, schema_version1 and digest domain `adaptive-factory.m8-cohort-evidence/v1`, while constructor/parser minimum now1. `factory/contracts/jsonschema/earned-autonomy.v1.schema.json` retains `urn:adaptive-factory:m8:earned-autonomy:v1` with minimum1. The prior released contract required30.

Real consumer inventory: repository search across factory/src, scripts and .grok-stack finds CohortEvidenceV1 parsing/evaluation only in the autonomy module; evaluate_autonomy checks this type and emits AutonomyProfileV1/PromotionRecommendationV1. In-tree calls found in autonomy tests, not a network handler/queue/persisted runtime adapter. Canonical M7 bridge remains recommendation-only, currentness_available=false and external_acceptance_available=false. OwnerRuntime is separate and never consumes CohortEvidenceV1. Therefore this is a concrete same-wire-identity compatibility hazard; no live mixed-version outage or authority escalation is established.

Compatibility is directional: new reader accepts legacy minimum30 data, so do not describe this as all backward compatibility breaking. A new producer's schema_version1/minimum1 payload is rejected by the previous v1 consumer without a version discriminator. The user approved one accepted task and release2.2.0; that authorizes changed semantics, not erasing the prior wire identity. A source package minor version alone does not distinguish serialized cohort messages.

Exact private probe, prefix `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:. taskset -c 0-3 python3 -c`:

```python
import subprocess,sys,types
from factory.tests.test_autonomy import valid_cohort_payload
from adaptive_factory.autonomy import CohortEvidenceV1
from adaptive_factory.contracts import ContractError
body=subprocess.check_output(["git","show","2a8e3839a469b3e05da167e9d8a807bf18e6adbf:factory/src/adaptive_factory/autonomy.py"],text=True)
old=types.ModuleType("adaptive_factory.review_predecessor_autonomy")
sys.modules[old.__name__]=old
exec(compile(body,"predecessor_autonomy.py","exec"),old.__dict__)
payload=valid_cohort_payload(1)
payload["minimum_human_acceptances"]=1
current=CohortEvidenceV1.from_dict(payload)
print("current:",current.schema_version,current.minimum_human_acceptances,current.DOMAIN)
try: old.CohortEvidenceV1.from_dict(payload); print("predecessor accepted unexpectedly")
except ContractError as exc: print("predecessor rejected:",exc)
legacy=valid_cohort_payload()
print("old valid input retained:",CohortEvidenceV1.from_dict(legacy).minimum_human_acceptances)
```

Observed exit0: current `1 1 adaptive-factory.m8-cohort-evidence/v1`; predecessor `invalid_integer: minimum_human_acceptances`; old-valid input retained30. Prior module was executed only from Git source bytes in a separate in-memory namespace; no candidate file altered. Current nested bridge code is unchanged for this comparison.

Smallest compatibility-correct recommendation if canonical one-task inputs remain required: preserve old CohortEvidenceV1 parser/constructor/schema floor30 and domainv1; add an explicit CohortEvidenceV2 with schema_version2, domainv2 and minimum1, zero invalid. Its schema may reuse unchanged nested v1 tuple/task/M7 types; do not gratuitously version all nested contracts or M7/M9. Dispatch the evaluator explicitly for supported v1/v2 cohort inputs and retain all currentness/security gates. Do not silently reinterpret storedv1 or automatically rewrite signed/digested old bytes. Add compatibility tests: priorv1 retained, v1/min1 refused, v2/min1 accepted, unknownversion/zero refused, distinct digest namespace, and unchanged recommendation-only behavior. Update AC001's implementation-specific V1 naming and inventory bindings coherently while retaining the owner's actual minimum1 outcome. Additivev2 support alongsidev1 fits minor2.2.0. A smaller alternative, only if canonical lower-floor requirement is deliberately dropped, is leaving empiricalv1 unchanged and using already-distinct new OwnerPolicyV1 for the one-case owner path; do not choose that silently against current AC001.

## Finding2: profile digest is a fixed capability label, not current-route binding

`factory/src/adaptive_factory/owner_autonomy.py:368` hashes only a literal `task_class=low_risk_text_only`, L1/L2, LOCAL_ACTIONS and external_authorityfalse. current_context never reads active-route.json. RequirementAC002 promises current-profile/scope revalidation and the repository contract identifies active route as local workflow authority. A profile_digest that remains fixed when route identity/risk/domains/quality profile/gates change does not provide that currentness property.

Private actual CLI probe: with clean cloned source and no active route, `python3 scripts/grok_m8.py activate` returned exit0/active/L1. `PYTHONPATH=factory/src python3 -c 'from pathlib import Path; from adaptive_factory.owner_autonomy import current_context; print(current_context(Path.cwd()).profile_digest)'` returned `6f262ffe4555f5b6cb3df8501a03d3d4079fa09e0b3f97c8eb989a167d011339`.

Using apply_patch only in scratch, added ignored `.grok-stack/runtime/active-route.json`:

```json
{"schema_version":1,"route_id":"review-changed-route","intent":"feature","risk":"high","domains":["security"],"quality_profiles":["base","security"],"human_gates":["security_review"],"allowed_agents":[],"task":"synthetic route-profile substitution"}
```

Repeated exact profile command returned the identical digest; `python3 scripts/grok_m8.py admit --action local_test` returned exit0, allowedtrue/L1/admitted, ceilingL2/external_authorityfalse. This input substitution survives the intended profile-change refusal claim. Not an external authority bypass: admitted action remains a bounded local_test decision, and CLI executes no arbitrary task. Also not proof this synthetic document passes the normal route loader; it demonstrates route absence/replacement/malformed authority is entirely unobserved by this consumer.

Bounded recommendation: derive profile from the validated current authoritative route and relevant local policy, not a caller-supplied digest. Include route identity and semantic risk/domains/quality profiles/human gates (and any existing authoritative policy binding needed by those fields), refuse absent/malformed/unsupported context, and make prior activation stale on relevant changes. Avoid volatile phase/timestamps that would gratuitously invalidate every status change; establish an explicit normalized projection. Keep L1 local_read/local_test and externalfalse; do not invent L2 promotion or blanket claims that all security tasks prohibit local reads/tests. If designers deliberately intend route-independent local capability qualification instead, rename/document that scope and remove low_risk_text_only/current-route implications; that is a requirements decision, not proof existing advertised profile binding works.

## Limits and conclusion

The separate root executable-inventory omission was not re-probed; another selected review seat owns that finding. No deployment, external approval, protocol traffic, live M7 cohort or production incident was investigated. Earlier reviews/full gate are not reissued here and no pass receipt is asserted. Both findings warrant a bounded correction/explicit compatibility ruling before merge; neither justifies broad architecture changes, another service, deployed policy changes or unrelated P0 repairs.

Candidate before/after checks: `git rev-parse HEAD`, `git status --porcelain=v1`, and `PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'` produced the unchanged identities above. No more candidate observations after this triage.

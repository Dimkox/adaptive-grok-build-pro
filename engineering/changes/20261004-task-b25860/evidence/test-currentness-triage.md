# Source-bound PR245 currentness/profile reproduction

HOLD: both reported claims reproduce. This is a bounded triage report before repair, not an independent full-branch re-review or completion receipt. The coordinator reports a full local PASS at01:26:33 for currentf839; a source repair invalidates that identity and requires fresh applicable gates. No previous result is relabelled or skipped here.

Candidate <repository-root>/.review-scratch/m8-one-task-autonomy; routeb258608f2ced, actualbase2a8e3839a469b3e05da167e9d8a807bf18e6adbf. Exact candidate before/after: HEADf8393ea5ba3bd8d014e46fa947d20fd78362247d; fingerprint8dea75f544f20a45fc306af003b46019a90aa28e576116e8b8466978396827b9; cleanstatus.

reviewed-tree-modified: no

Startup2026-10-05T01:32:03Z independently remeasured/recorded privately before route/source inspection:14physical/28online logicalCPUs0-27, defaultprocess22/affinity0,1,8-27, actual root-mountedcgroup2/user.slice/user-1000.slice/session-2050.scope, inheritedcpuset0-27, ancestorquotasmax100000, rootcpu.maxabsent. Bounded child-onlytaskset0-27probe verified28/samecgroup/quota; reviewer oneprocess0-3<=4CPUs. Trusted owned nonsticky.review-scratch0700; fresh private0700child <repository-root>/.review-scratch/test-review-m8d-Ha7JJd.

Private exact scratch <repository-root>/.review-scratch/test-review-m8d-Ha7JJd/snapshot created with `GIT_OPTIONAL_LOCKS=0 git clone --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/test-review-m8d-Ha7JJd/snapshot`. Initial HEAD/fingerprint matched candidate. Only private origin config was set tohttps://github.com/Dimkox/adaptive-grok-build-pro.git, without network. Candidate observations useGIT_OPTIONAL_LOCKS=0/PYTHONDONTWRITEBYTECODE=1. Private mutations usedapply_patch; restored rootfile/removed private test route, resulting scratch status clean and fingerprint identical again. Activation persists only in ignored private scratch runtime.

## Exact real-CLI reproduction

Private probe.py is included beside this report. It imports actual current_context(root), prints its wirefields, invokes real `python3 <scratch>/scripts/grok_m8.py activate` optionally and `admit --action local_test` with separate subprocesses, captures exact exit/stdout/stderr. No local test execution occurs.

Exact commandprefix E: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-3 python3 <repository-root>/.review-scratch/test-review-m8d-Ha7JJd/probe.py` (cwdprivate snapshot).

1. `E absent-route --activate`: scratch has no active-route.json (ignored runtime absent from clone). Observed activateexit0 allowedTrue/L1/reasonactive; admitexit0 allowedTrue/L1/reasonadmitted. All outputs ceilingL2/external_authorityFalse. Contextsource_digest7dc6a1944093dd120429a8f4950874edfb511776be028b0cd45555f1eaa7688c, profile_digest6f262ffe4555f5b6cb3df8501a03d3d4079fa09e0b3f97c8eb989a167d011339.

2. Added comment immediately after futureannotations in trackedprivate tests/test_structure.py usingapply_patch. `E changed-root-test`: source_digest identical7dc6a1944093dd120429a8f4950874edfb511776be028b0cd45555f1eaa7688c, profile identical; actualadmitexit0 allowedTrue/L1/admitted. Claim4180008509 reproduced; mutant survives source-currentness gate. The comment is enough to prove the file's bytes are absent from binding; no harmful test was executed.

3. Created ignored private .grok-stack/runtime/active-route.json:

`{"schema_version":1,"route_id":"review-high-risk-production","change_id":"review-high-risk-production","intent":"incident","risk":"high","domains":["security","production"],"task":"production security incident","status":"routed","allowed_agents":[],"analysis_agents":[],"review_agents":[],"human_gates":["security_approval"],"quality_profiles":["security"],"required_evidence":["verification"]}`

`E high-risk-security-production-route`: bothsource/profile digests unchanged; actualadmitexit0 allowedTrue/L1/admitted. Removed exactly that private routefile viaapply_patch. `E removed-route`: samecontext digests/admitexit0 allowedTrue/L1/admitted. Claim4180008514 reproduced; changed/absent route survives admission profile gate. Eachresult external_authorityFalse and ceilingL2. All subprocessstderr empty.

## Actual boundary and implications

current_context inventories only factory/src, factory/contracts, one ownerpolicy, scripts/grok_m8.py andVERSION (plus relevantuntrackedpaths), withGitHEAD andGitdirbinding. Tracked root tests, other executed root scripts, rootcontracts/architecture and other worktreebytes are not in that source digest. Profile is a hardcoded low_risk_text_only dictionary; current route is not read. The direct coreOwnerContextV1 API validates digestshape, then compares supplied digests against persistedactivation, but CLI derives only that narrower surface.

The allowlist and structured output remain authoritative within this standalone advisory decision API: external actions andlocal_edit are denied, externalauthorityfalse, revocation/expiry and the bytes it actuallyinventories are enforced. The CLI does not execute tests/commands, dispatchworkers, issuegrants or bypassexternalTrustCI. Thus these findings do not demonstrate production/merge escalation or arbitrary execution. They do demonstrate incomplete advertised current-source/profile and missing/staleinput controls forlocal_test admission, and could mislead a future consumer relying on that decision. Recommended bounded repair: bind complete relevant executed workingtreeinventory and actual validated currentroute/profile; failclosed for absent/malformed/highrisk/security/production scope and revalidate peruse, with actualCLI rootfile/route regressions. No externallyauthoritative approval is implied by local routebinding.

No new tests/fullsuite/providers/agents/secrets/network/externalwrites in this triage. No exhaustive arbitrary-file inventory or routevalidation campaign was executed; pending repairdesign and independent changed-source review remainunexecuted. Both reproduced mutant outcomes are SURVIVED, concrete findings, notPASS. Candidate restoredidentity unaffected; all observations stopped before writerstarts.

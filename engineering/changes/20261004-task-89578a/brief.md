# Local verifier fail-fast and bounded delivery cycle

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261004-task-89578a`
Created: 2026-10-04T19:53:48+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

feature: optimize local verification with fail-fast required-check refusal and bounded committed-HEAD checks; preserve receipts, full PR scope and external Trust CI; batch fixes and freeze reviewed candidates

## Outcome

Stop local verification after a decisive required refusal, retain the actual failed result and fingerprint-bound failure report, and explicitly disclose checks not executed. Successful PR/release scope, independent review, external exact-head Trust CI and branch protection remain unchanged. The user approved implementation of the preceding bounded optimization proposal.

## Scope

### In scope

- Existing verifier/CLI/tests and concise delivery instructions; reuse existing fast behavior where possible. Committed-HEAD short checks must use the same Core import environment and cannot replace full gates.
- Batch review fixes through the same writer, persist complete reviews before freezing, overlap final local verification and exact-head external check only after delegated UNVERIFIED branch transport.

### Out of scope

- No new service, framework, dependency, generic cache, root entry or deployed Trust CI change. No human approval, branch-protection change, direct main push, release/tag or Git history rewrite.

## Constraints

- Backward compatibility: successful verification retains its selected checks and receipt contract. Diagnostic continuation may use an explicit opt-in if necessary; unexecuted is never passed or silently reused.
- Data/privacy: public evidence uses neutral relative paths, no operator home/network identity.
- Performance: short iteration target180s; no guarantee that the mandatory full successful gates fit that budget.
- Operational: exact original base ee3911869419204154e02900e58bf31492ee744c, one application writer, no edits during final checks.

## Dependencies and resource schedule

Startup snapshot recorded before route inspection at 2026-10-04T19:51:32Z:14 physical/28 online logical CPUs; controller affinity0,1,8–27; inherited effective cpuset0–27; no finite ancestor quota observed. Bounded child-only widening verified28 CPUs0–27; controller unchanged. Platform13 slots and route cap10 are independent limits.

1. Four independent read-only route analyses in one wave: repo_explorer (control flow), architect (minimal safe design), docs_researcher (existing fast mode/instructions), integration_architect (receipt consumers). No nested agents. At most four lightweight worker processes across this wave.
2. Coordinator invokes the startup PR selector with verified allocation before heavy verification. Analysts return concise reports out-of-band; coordinator persists them before assigning sole application writer general_implementer.
3. Writer reproduces RED then GREEN; committed-HEAD short controls use the actual Core environment. Full preflight precedes the two route-selected independent reviewers, dispatched together.
4. After all reviews finish, coordinator persists complete reports and commits final candidate. Final local PR and external exact-head gates may overlap after exact delegated unverified transport; no source changes during those gates. An identical merged tree is a no-op, not another full rerun.

No named human gates on route89578a99758f. Prior explicit user implementation approval applies to this bounded existing-flow change. Technical rulings are recorded here rather than prompting again.

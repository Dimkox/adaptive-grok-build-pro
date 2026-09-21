# Parallel issue execution — 2026-09-21

The user asked which issues remain, then explicitly requested starting all remaining issues in parallel. All 65 open issues have been assigned to source-based analysis. This research route has no application-code writer; each correction uses its own independent route and worktree.

Read [issue-queue.json](issue-queue.json) for all rows, dependencies, branch/route identities and next actions. Five analysis reports cover the complete inventory; follow-on design packets make broader issues concrete. Existing open PRs are reused; reports distinguish exact-head success from stale-base evidence and historical symptoms from current defects.

## Work started

- #156, #162 and #166 have independent implementation branches based on frozen PR170.
- #153/#161, #168 and #147/#148 have independent successor routes with completed selected analysis.
- Remaining local defects have bounded design packets or retained candidate refs.
- External tool/consumer issues carry a precise ownership/target boundary; historical fixes carry closure evidence without pretending their GitHub issues are closed.

## Limits and next action

The research report is not local product completion or merge authority. Product branches still need their selected checks/reviews and exact-head external Trust CI. Keep database-heavy tests in one lane; other analysis, writing and review can run in parallel. Do not rewrite or duplicate the 17 existing PRs blindly, close issues without authority, or mutate deployed services/policy.

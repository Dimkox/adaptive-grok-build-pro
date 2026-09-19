# Proposed design — preserve risk-bearing intent

## Decision for human approval

Remove `pull request` and ` pr ` as standalone review-intent triggers. They name the delivery mechanism, not the user's request. Intent precedence is incident, bugfix, release, then review: release intent wins when release and review wording co-occur, while bugfix and incident retain their higher precedence. Standalone explicit `review`, `review pull request`, and `code review` remain review routes.

A generic implementation task that mentions only `pull request` or `PR` remains feature intent and retains its write owner; delivery nouns alone do not create a review route.

## Route contract

Regression tests compare full route outputs, not only `intent`: intent, risk, human gates, review agents, required evidence, quality profiles/workflow skills, and single write owner. Paired release wording with and without pull-request references, including a release prompt that also requests review of its rollout, must preserve the same release control set. Standalone explicit review wording must still select the ordinary review control set. A release installer bugfix remains a bugfix under bugfix-before-release precedence.

No route schema migration is needed. Existing serialized routes retain their original fields; only fresh task classification changes. Reviewers should verify intent suppression is no longer possible through delivery nouns alone.

## Security and recovery

This fix restores the router's intended higher-control release classification; it does not make local human gates an enforcement mechanism and does not alter delegated grants or Trust CI. Rollback is a revert of the keyword/test change. No external operation is performed.

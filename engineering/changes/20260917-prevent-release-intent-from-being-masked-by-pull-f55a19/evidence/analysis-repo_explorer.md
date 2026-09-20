# Repository exploration: issue #123

Inspected exact base `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217` in `/tmp/adaptive-fix-release-routing`; no source files were changed during this analysis.

## Reproduction

Called `build_route(Path('.'), prompt)` once for each prompt on that base. Appending delivery wording changes all three release examples from `intent=release`, `risk=high`, gates `scope_and_design_approval` + `production_action_approval`, reviews `security_reviewer` + `release_reviewer`, and workflow `release-readiness` to `intent=review`, `risk=medium`, no human gates, reviews `code_reviewer` + `test_reviewer`, and workflow `verification-evidence`:

| Without PR wording | With PR wording | Observed effect |
|---|---|---|
| `Release sync 2.0.18 to 2.0.19 identity bump R with release` | same + `landing rows for the pull requests merged since v2.0.18` | release → review; gates disappear |
| `build(release): deliver deterministic v2.0.19 ZIP and sidecar and publish the GitHub release` | same, replacing publish clause with `for the merged release-sync pull request` | release → review; gates disappear |
| `release the artifact and tag it` | `release the artifact for the merged pull request and tag it` | release → review; gates disappear |

This reproduces the issue’s cause: `_best_intent` checks `review` before `release`, and `INTENT_KEYWORDS['review']` treats `pull request` as a review keyword. Release-specific risk, workflow, reviewer, evidence and gate selection all consume the single resulting `intent`, so one transport noun changes downstream controls without a warning.

## Existing coverage and boundary

`tests/test_repo_router.py` covers an explicit code review of a PR (`test_review_has_no_write_owner`) and a production release with a canary (`test_release_has_no_write_owner_and_human_gate`), but contains no paired release prompts with/without pull-request wording. Existing priority comment in `_best_intent` calls out defects, release, review and architecture but does not guarantee the release control floor when a delivery noun overlaps.

I also checked adjacent cases. `fix the release installer keep list` remains `bugfix` because bugfix precedes release; this is a desirable priority and should stay intact. `incident response for pull request issue` stays high-risk incident with its incident skill, although it lacks the production action gate unless production/deploy is named. Ordinary `document ... pull request ...` wording can likewise be classified as review, but that is outside the release-gate defect and should not expand this fix without explicit acceptance criteria.

## Minimal behavior recommendation

Make `pull request` / ` pr ` transport terminology cease to match the `review` intent. An actual review request still matches the explicit `review`, `code review`, or localized review phrases; consequently “review this pull request” remains review. Keep bugfix ahead of release so the installer counter-case stays a bugfix. Add table-driven paired release prompts asserting release intent, high risk, both release gates, release reviewer, and release-readiness skill, plus the installer counter-case and a real PR review case. Moving all release classification ahead of review is a viable conservative alternative, but would classify requests explicitly reviewing a release PR as a release operation; dropping transport-only review keywords is narrower.

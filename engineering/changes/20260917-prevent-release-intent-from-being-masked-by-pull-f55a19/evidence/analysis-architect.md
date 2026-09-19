# Architect analysis — issue #123

## Finding

The defect is in intent detection, not the serialized route contract. `.grok-stack/adaptive_grok/router.py` currently treats `pull request` and the fragment ` pr ` as review-intent keywords. `_best_intent()` returns the first matching high-priority intent and places `review` before `release`. Thus a release instruction can be downgraded solely because its description names the mandated delivery mechanism. On the reproduced wording this changes intent/risk, removes the release human gates, swaps release/security review for ordinary code/test review, and omits the release-readiness workflow skill.

The keyword is semantically ambiguous: “review this pull request” expresses review intent, but “publish the release through a pull request” names transport. It should not independently establish review intent. The explicit verb “review” already classifies actual PR review requests.

## Recommended bounded design

Remove delivery-mechanism-only terms (`pull request`, ` pr `) from `INTENT_KEYWORDS['review']`. Keep explicit review verbs/phrases there. Preserve the existing intent precedence, especially bugfix ahead of release: the issue’s “fix the release installer” counterexample should remain a bugfix, while explicit release intent plus only a PR transport reference stays release. Do not simply move release ahead of review globally: an explicit request to review a release change can be a review, not a publication action.

Add table-driven route tests for paired prompts that differ only by the PR transport clause, covering release, incident, bugfix, and docs as requested by the issue. Assert the relevant route controls, not just `intent`: release risk, both gates, release reviewer and release evidence/skill; bugfix remains bugfix; explicit PR review remains review. Include the release-installer counterexample and release wording with deployment terms. Ensure no tested release/production-action case loses its production gate. Keep risk and gate derivation conservative if future intent overlap remains.

## Contract and compatibility

No new route field is needed for this bounded repair. Preserve the current schema-version-1 route JSON shape and the meanings of `intent`, `human_gates`, `review_agents`, `required_evidence`, and `workflow_skills`. Removing accidental transport-based review matches is a behavior correction; an explicit “review … pull request” remains compatible because “review” itself is still a review keyword. A new masked-intent field or multi-intent schema would enlarge the protocol and its consumers without being necessary for the reproduced defect.

The current route schema is represented by the `Route` dataclass and serialized with `asdict`; no separate route JSON schema was found in the inspected tree. Existing consumers expose route fields in context and workflow artifacts, so avoid renaming or reshaping them.

## Scope and trust boundary

This change should repair local route construction and its characterization tests only. It must not claim that a populated `human_gates` list is itself an approval or independently enforced production authorization. The router constructs workflow controls; actual delegated grants and Trust CI signed approvals remain separate authority. Whether downstream workflow blocks progress when route gates are outstanding is a distinct enforcement question (tracked separately as issue #126), and this fix must not weaken it or modify deployed Trust CI policy.

No repository source, route contract, deployed trust material, or product file was changed for this analysis.

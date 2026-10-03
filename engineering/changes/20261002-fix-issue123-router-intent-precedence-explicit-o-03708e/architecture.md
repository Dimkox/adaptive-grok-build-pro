# Architecture — Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The priority ladder chooses bugfix/review before raw release scores. Consequently PR transport masks an explicit release and any release noun can escalate otherwise ordinary work. The immutable old router added controls for every raw release substring; that does not meet the approved contextual exclusions.

## Proposed behavior

Detect a bounded affirmative operation independently of raw scores. Exclude quoted spans, history and coordinated negative clauses. Replace only the release score with that semantic signal; prioritize incident, affirmative release, bugfix, review, then the existing lower ladder. Preserve ordinary review/PR vocabulary.

Review repair binds historical markers and command negation to instruction prefixes, while direct past-state predicates distinguish declarations from relative artifact-history clauses. Carry descriptive plan-infinitive context across comma/and continuations, and recognize supported plural descriptive nouns. Object history, destination restrictions and artifact omissions do not negate the requested operation.

Release includes delivery reviewers so moving a mixed review/release prompt into the operational route cannot discard code/test evidence. Explicit operations add release-readiness and production-action approval even when incident containment wins the label.

## Components and boundaries

Only router.py and tests/test_repo_router.py change product bytes. Repository classification, risk/domain detection, workflow authority, grant binding, external Trust CI and approval code remain independent.

## Data flow

Prompt → quote/context filtering → affirmative-operation boolean → deterministic intent → existing route construction, reviews/evidence/gates. The boolean is not persisted as a new schema field and never authorizes an action.

## API and event contracts

No HTTP/event/schema change. Persisted Route fields retain their existing meanings; corrected intent changes selected obligation values. Hooks and reasoning policy are downstream compatibility consumers.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- No governance rule, canonical example or debt record changes. Local verification and independent reviews remain separate from external exact-head merge trust.

## Bitrix-specific impact

- No Bitrix component or installed-core changes.

## Decisions

Keep incident priority. An explicit operation outranks bugfix/review because the requested publication still needs operational handling; a bugfix about a release installer remains a bugfix. Preserve conservative raw risk/domain checks instead of weakening safeguards for contextual deployment mentions.

## Risks and mitigations

Deterministic language support is deliberately finite. Literal positive/negative bilingual cases document coverage; unrecognized phrasing remains a limitation, and existing raw safety signals can retain additional gates. No permission, deployment, publication or merge occurs here.

Both initial independent reviews failed on exact HEAD e1c7a01d3fe057c90e80e547c42aadddbae99d11 despite that HEAD's full PR verifier passing. Those complete reports are retained unchanged as historical failure evidence; repaired candidates require fresh controller verification and independent review.

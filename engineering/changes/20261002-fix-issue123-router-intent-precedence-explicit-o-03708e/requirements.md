# Requirements — Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- AC-001: explicit supported English/Russian operations survive PR, review and fix vocabulary.
- AC-002: negation, quotes, history and release nouns do not create operations; a new independent affirmative clause can.
- AC-003: preserve no-write release ownership, all delivery/security/release evidence and existing human gates; incident retains its writer and containment skill.
- AC-004: ordinary route contracts and downstream hooks/reasoning remain compatible.

## Failure and edge cases

- Supported requests are direct commands, polite English requests, English want/need-to and Russian need/request prefixes; release preparation and canary rollout are explicit operational requests.
- Quotes include straight/curly double quotes, single quoted examples, backticks and fenced code. Incomplete quoted spans are excluded conservatively.
- Semicolon/newline/sentence boundaries and contrast words reset instruction context; comma/and lists carry command negation, historical prefixes and descriptive plan infinitives.
- Historical prefixes and direct past-state declarations describe prior instructions. Current release commands may target artifacts built/reviewed in the past; relative clauses are object qualifiers. Command-prefix negation suppresses the operation, while object/destination modifiers such as Russian `без`, English `with no need to restart` and `not to production but to staging` retain the affirmative action.
- Singular/plural release plans, checklists, workflows and policies remain descriptive. A review of a plan to deploy and publish retains its review intent; a separate publish command after a semicolon requests an operation.
- Numeric version periods remain inside their token; actual sentence delimiters still reset instruction context. Direct historical declarations admit up to three subject tokens while excluding relative markers (`that`, `which`, `who`, Russian `котор...`); existing object-relative positives keep complete operational controls. Supported Russian plan forms carry infinitive context across coordination with or without a colon.
- This bounded grammar is not general natural-language understanding. Conservative risk/domain signals remain independent and may still add gates for negated or descriptive deployment text.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- No canonical governance JSON, rule digests or examples change.
- Approved source design section B governs this reconstruction; old dirty worktree is read-only intent context, never fresh evidence.

## Non-functional requirements

- Security: no operational authority from classification; no secret or deployed-system access.
- Reliability: literal regression expectations, existing incident containment, and explicit workflow obligation checks.
- Performance: pure local regex matching with no external service or dependency.
- Observability: route fields expose selected intent, reviews, evidence and gates.

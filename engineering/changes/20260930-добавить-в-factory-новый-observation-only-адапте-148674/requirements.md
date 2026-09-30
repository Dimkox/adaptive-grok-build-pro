# Requirements — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Closed registry v1 rejects unknown fields, duplicate identities, non-HTTPS endpoints and embedded secret values.
- [ ] Selection is deterministic and skips a model while its bounded cooldown is active.
- [ ] Retry/fallback occurs only before any response bytes are observed and within the reserved attempt/token budget.
- [ ] HTTP 401/402 and provider daily-limit signals stop the sequence without trying another identity.
- [ ] Evidence binds tenant/task/run/attempt/fence/budget and contains usage counts, outcome and sanitized reason only.
- [ ] Runtime stays disabled by default; live/provider qualification remains `NOT_RUN`.

A criterion that declares a set of expected outcomes must stay falsifiable and
achievable. Naming an exact set — `the cutover reds are exactly {key-a, key-b}` —
obliges a per-member executable liveness probe: the same criterion must reference
one repository-contained `unittest.TestCase` selector whose AST calls
`exercise_expectation_member("key-a", observe=…, mutate=…, undo=…)`. The validator
resolves this structure without importing the test; the ordinary test run proves
the member absent before mutation, present after mutation, and fully restored by
undo. A member no detector can produce cannot be proven that way, so declare the
set as an upper bound (`observed ⊆ {…}`) and assert non-emptiness. Quantifier cues
apply only to their brace group's sentence.

## Failure and edge cases

- response already started: preserve ambiguity and stop;
- unknown usage: record incomplete accounting, never synthesize zero;
- malformed transport result or registry: fail closed;
- exhausted cooldown set: report unavailable rather than bypass cooldown.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: secret names may be configured; secret values are never inputs to or fields of this adapter.
- Reliability: bounded attempts, bounded cooldown and deterministic ordering.
- Performance: no network probes during selection; at most the reserved number of attempts.
- Observability: immutable per-attempt records plus terminal status and registry digest.

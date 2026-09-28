# Requirements — Reject unsatisfiable expectation-set members in typed specs at plan time

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001 — Given a criterion that declares the exact set containing a proven member `css-link-count` and an
  unproven member `frozen-plan-text`, when the spec is validated, then validation fails with a finding that
  names `frozen-plan-text`, the criterion id and the missing executable mutation/undo proof.
- [x] AC-002 — Given an exact declaration whose members are achievable, when each is bound by a resolvable
  `unittest.TestCase` selector that calls `exercise_expectation_member` with its literal member and
  observe/mutate/undo callables, then static validation and ordinary test execution pass.
- [x] AC-003 — Given a criterion that declares the set only as an upper bound, when non-emptiness is not
  asserted, then validation fails because an empty observation would satisfy the criterion; when
  non-emptiness is asserted, validation passes.
- [x] AC-004 — Given ordinary prose containing an empty brace group, numeric group, singular placeholder,
  JSON literal, cross-sentence unrelated cue, or a brace list with no local quantifier, validation produces no
  expectation-set finding; exact multi-member short IDs such as `{A, B}` remain checked.
- [x] AC-005 — Given every change package already recorded under `engineering/changes`, when the repaired
  validator and the exact route-base validator each gate-validate the base inventory, then both return
  identical full error lists using only committed Git inputs.

## Failure and edge cases

- Non-mapping criterion items, a non-string `statement`, and a non-string evidence value are skipped without
  raising; the shape errors remain the schema's job (`test_malformed_criteria_are_skipped_not_crashed`).
- A dashed declared member (`css-link-count`) must be matched by an underscored or differently-cased probe
  only through its exact helper literal; selector text alone is never proof.
- One selector may prove several members with separate helper calls; a member can never be assembled across
  evidence entries, and a nonexistent, pass-only, lookalike-helper, or wrong-literal selector fails closed.
- `receipt`, `attestation` and `production_signal` evidence never proves liveness (INV-003).
- The obligation fires in the draft profile as well as at the gate, so a dead member is visible the moment
  the sentence is written and not only when the package is closed.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none declared; no governance rule, canonical example or debt entry changes.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: issue #202 proposal items 2 and 3 are accepted as out of
  scope here and recorded in `brief.md`; item 3 is blocked by historical-package evidence immutability.

## Non-functional requirements

- Security: no new filesystem, network or subprocess access; the validator continues to read only the
  descriptor-bounded spec bytes already loaded by `load_spec`.
- Reliability: deterministic static AST inspection plus ordinary executed tests; no test module is imported by
  validation and no cache or external state is consulted.
- Performance: bounded by existing statement/criterion/evidence limits and a 1 MiB cap per referenced source;
  the committed route-base census currently covers 98 packages.
- Observability: `SIG-001` (`change_spec_gate_findings_with_reason_liveness_proof`) is read from
  `python3 scripts/grok_spec.py validate --gate --json` and from the `change-spec-invalid` verifier finding.

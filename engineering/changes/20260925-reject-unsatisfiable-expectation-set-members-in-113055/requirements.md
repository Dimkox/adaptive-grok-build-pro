# Requirements — Reject unsatisfiable expectation-set members in typed specs at plan time

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001 — Given a criterion that declares the exact set containing a proven member `css-link-count` and an
  unproven member `frozen-plan-text`, when the spec is validated, then validation fails with a finding that
  names `frozen-plan-text`, the criterion id and the missing liveness proof.
- [x] AC-002 — Given the same declaration, when every declared member is named by `test` evidence of that
  criterion, then validation passes, so the obligation is discharged by a probe rather than by rewording.
- [x] AC-003 — Given a criterion that declares the set only as an upper bound, when non-emptiness is not
  asserted, then validation fails because an empty observation would satisfy the criterion; when
  non-emptiness is asserted, validation passes.
- [x] AC-004 — Given ordinary prose containing an empty brace group, a numeric or single-character
  placeholder, an all-uppercase template variable, a JSON literal, or a brace list with no quantifier, when
  the spec is validated, then no expectation-set finding is produced.
- [x] AC-005 — Given every change package already recorded under `engineering/changes`, when the repaired
  validator and the shipped validator each gate-validate it, then both return identical error lists.

## Failure and edge cases

- Non-mapping criterion items, a non-string `statement`, and a non-string evidence value are skipped without
  raising; the shape errors remain the schema's job (`test_malformed_criteria_are_skipped_not_crashed`).
- A dashed declared member (`css-link-count`) must be matched by an underscored or differently-cased probe
  name (`test_liveness_CSS_LINK_count.py`), otherwise the rule rejects truthful probes.
- One probe may name several members; evidence naming a *different* member must never stand in as a proof.
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
- Reliability: deterministic and pure — the same document yields the same findings on every run; no cache and
  no state is consulted.
- Performance: bounded by the existing 4096-character statement and 500-criterion limits; the full historical
  sweep over 106 packages stays under one second.
- Observability: `SIG-001` (`change_spec_gate_findings_with_reason_liveness_proof`) is read from
  `python3 scripts/grok_spec.py validate --gate --json` and from the `change-spec-invalid` verifier finding.

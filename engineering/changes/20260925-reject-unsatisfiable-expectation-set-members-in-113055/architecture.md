# Architecture — Reject unsatisfiable expectation-set members in typed specs at plan time

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`validate_spec` checks the *shape* of a typed specification: identifier grammar, bounded strings, unique
criterion ids, resolved production signals, existing test and contract paths, and — at the gate — evidence,
non-`UNKNOWN` objective fields and risk-tier obligations. A criterion statement is free text, so a sentence
declaring a set of expected outcomes ("the cutover reds are exactly X, Y") is validated only as text: nothing
asks whether every declared member can exist given the rest of the rules. The defect surfaces months later as
an implementer's judgment call, where the two available doors are both wrong — trust reality and deviate from
typed authority, or trust the text and break a higher rule such as evidence immutability.

## Proposed behavior

`expectation_set_findings(spec)` reads the recorder's own declaration and makes it falsifiable:

- A brace group yields the declared members; only identifier-shaped names count, so `{}`, `{0, 1}`, `{X}`,
  `{TITLE}` and `{"a": 1}` stay inert.
- An exactness cue obliges a per-member liveness proof: each member must be named by `test` evidence of the
  same criterion, matched on token sequences so `css-link-count` is satisfied by
  `test_liveness_CSS_LINK_count.py` or a test selector. The existing evidence-path check makes that probe a
  file that must really exist.
- An upper-bound cue obliges a non-emptiness assertion, because otherwise an empty observation satisfies the
  criterion.
- Both profiles: findings are returned in the draft profile as well as the gate profile, so the author sees the
  contradiction while writing, and the verifier surfaces them as `change-spec-invalid` findings.

## Components and boundaries

`.grok-stack/adaptive_grok/spec.py` owns the rule (pure, no I/O beyond the already-bounded spec read). The
callers stay untouched: `scripts/grok_spec.py validate --gate` prints the errors, and
`verification._change_specs` turns each error into a `change-spec-invalid` finding.
`schemas/change-spec.schema.json` gains an annotation on `$defs.criterion` only; the template and the
`adaptive-delivery` skill gain prose so the obligation is known before it is enforced.

## Data flow

spec bytes → `load_spec` (strict canonical JSON) → `validate_schema` (frozen shape) → `_semantic_errors` →
`expectation_set_findings` → error list → CLI JSON / verifier findings. No new store, queue, cache or external
service; nothing is written.

## API and event contracts

No HTTP API, event schema or OpenAPI contract changes. `schemas/change-spec.schema.json` is a declared contract
of this change package (bound into the spec fingerprint) and is modified only by a `description` annotation —
the accepted document grammar, required keys and limits are byte-comparable to before, which is why no schema
version bump occurs. The obligation deliberately reuses `id`, `statement` and `evidence`: the independent
holdout rejects any other criterion key, so a new field would produce a spec that is locally valid and
externally rejectable.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none; no governance rule, canonical example or debt record is created or retired.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none introduced.
- Expected governance handoff or receipt impact: none; receipts keep their current kinds and shapes.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none; the stack refresh ships the updated file through the existing payload list.
- Core modification: forbidden unless explicitly approved. Not applicable — no Bitrix core path is touched.

## Decisions

Satisfiability is enforced through the author's own declaration and the existing evidence grammar rather than a
new document field, because the deployed holdout freezes the criterion key set and repository changes cannot
modify it. Consequence: the validator proves that a *named probe exists*, not that the probe really reddens the
member — that remains review and execution evidence. The second proposal item of issue #202 (require the
referenced detector's read-path at the scope gate) was left out; it belongs to `verification_scope.py`, another
contour's file.

## Risks and mitigations

- Cue vocabulary is English prose, so a differently worded sentence can escape the obligation. Mitigation: the
  escape is visible in the criterion text during review, and the cue sets are one small constant block.
- A legitimate brace group could be read as a declared set. Mitigation: the identifier-shape and placeholder
  filters plus the `test_no_existing_package_declares_an_unsatisfiable_set` sweep over all 106 recorded
  packages, and the requirement that both a quantifier cue and a member list are present.
- Silent weakening (warning instead of rejection) would restore the defect. Mitigation: nine mutants of the
  rule, including a warning-only variant, each break the delivered tests.

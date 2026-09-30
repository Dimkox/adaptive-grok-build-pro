# Requirements — Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Bounded assembly rejects future features and change IDs spanning partitions while preserving non-product outcome counts.
- [ ] A fixed-seed temporal pilot emits reproducible versioned baseline/model artifacts and overall plus per-project discrimination/calibration metrics.
- [ ] A prediction made before the first independent check has a complete additive log-odds explanation bound to the model and feature snapshot.
- [ ] Insufficient history or explanation failure is `not_qualified`/`unavailable`; every output has `authority_effect=none` and cannot alter gates.

## Failure and edge cases

- Mixed attempts for one change are collapsed before splitting; a change cannot train and test.
- Infrastructure abort, pending, and unavailable are counted but never coerced to product pass/fail.
- Late features, unknown feature schemas, excessive examples/features/iterations, non-finite values, and one-class training data fail closed.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: offline numeric inputs only; no payloads, credentials, network, subprocess, or external writes.
- Reliability: canonical hashing and fixed arithmetic make identical inputs byte-reproducible.
- Performance: hard limits bound examples, features, and training iterations.
- Observability: artifact includes counts, split/model digests, baseline/model metrics, and project portability.

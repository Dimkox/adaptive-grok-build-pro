# Release plan — Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

## Deployment

Ship as an optional Python module with the Factory source. No service, migration, dependency, scheduled job, or live model is installed.

## Feature flags / staged rollout

No production caller is wired in this contour. A later separately reviewed caller may run the pilot offline and must preserve `authority_effect=none`.

## Metrics and alerts

Inspect status/reason, qualified/excluded counts, artifact/model digests, baseline/model AUC and Brier score, and per-project metrics. No alerting is created for an inactive pilot.

## Go/no-go criteria

Focused and PR verification pass, independent reviews pass, model artifacts reproduce, leakage controls reject, and no authority-changing integration appears in the diff.

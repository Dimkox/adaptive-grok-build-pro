# Rollback plan — Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

## Trigger conditions

Non-deterministic artifacts, accepted leakage, incorrect output-space/additivity, or any workflow authority effect.

## Application rollback

Remove/disable the optional caller first. Revert this isolated module and test change if contract-compatible forward repair is not immediate.

## Data recovery / forward-fix

No migration or authoritative state exists. Retain old observation artifacts by digest; publish a new version rather than rewriting them.

## Verification after rollback

Run existing prediction contract/qualification tests and confirm the normal rule-based workflow remains available without the module.

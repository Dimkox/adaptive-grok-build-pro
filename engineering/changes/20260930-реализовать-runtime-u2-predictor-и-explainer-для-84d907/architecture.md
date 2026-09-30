# Architecture — Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Closed observation and explanation v1 contracts validate caller-built artifacts, but no runtime assembles history, trains a model, evaluates it, or produces those artifacts.

## Proposed behavior

Add an optional dependency-free offline pilot that predicts first independent product-check failure. It fits a bounded deterministic standardized logistic model, compares it to a constant-rate baseline, and emits content-addressed model and explanation artifacts. It is observation-only.

## Components and boundaries

`prediction_runtime.py` sits beside the existing `prediction_contracts.py`. It performs no database, network, provider, route, permission, budget, test-selection, or M8 mutation.

## Data flow

Bounded historical rows → validate/collapse by change → temporal partition → train baseline and model → evaluate overall/per project → model artifact → candidate feature snapshot → closed observation and additive explanation artifacts.

## API and event contracts

The existing `prediction-observation.v1` and `prediction-explanation.v1` schemas remain unchanged. Runtime artifacts identify their own schema/model/preprocessing versions and use log-odds consistently.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

Use deterministic gradient descent rather than adding an ML dependency. Explain the linear log-odds model exactly: expected value plus every standardized feature contribution equals the model output.

## Risks and mitigations

Small/nonportable data can mislead: status remains observation-only and project metrics are explicit. Explanation is predictive, not causal. Insufficient history becomes `not_qualified`; explanation errors become `unavailable` without blocking the workflow.

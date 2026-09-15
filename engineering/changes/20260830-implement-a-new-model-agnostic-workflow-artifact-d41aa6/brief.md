# Workflow Artifact Adapters

Change ID: `20260830-implement-a-new-model-agnostic-workflow-artifact-d41aa6`; risk: red; domains: integration, security, API.

## Problem and outcome

GitHub Spec Kit and BMAD are not integrated, while Superpowers documents exist only as partial advisory planning/runtime artifacts and can drift from durable M1/M2/M3 packages. Add one safe compiler that imports explicit framework artifacts, builds a stable route-bound task graph, and blocks unresolved convergence drift without granting imported data any authority.

## Scope

In scope: three strict JSON schemas with shared runtime validation, bounded no-follow source and CLI-authority loading, closed Spec Kit/BMAD/Superpowers adapters, task DAG validation, deterministic convergence, source-status hints plus ephemeral receipt-derived effective status, read-only-default CLI with rollback-safe serialized CAS graph/report/projection/export publication, opt-in verifier integration, installer/package inventory, tests, and docs.

Out of scope: installing upstream frameworks wholesale; personas or agent orchestration; fuzzy/LLM extraction; network access; external writes; production deployment; database changes; approvals, merge, Trust CI policy, or GitHub Actions.

## Constraints

Historical packages without workflow manifests remain valid. Inputs are untrusted and bounded. The compiler uses only the Python standard library. Native M1/M2/M3/route contracts and external Trust CI keep their existing authority.

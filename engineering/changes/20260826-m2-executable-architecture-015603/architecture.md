# Architecture — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Architecture authority is absent. README's complete K16 graph is intentionally non-directional and cannot prove dependencies, trust, secrets, protocols, data classifications, failure contracts, or compatibility.

## Proposed behavior

Two strict JSON-compatible YAML documents become architecture authority. Dependency-free modules validate and normalize them, compute stable digests, compare exact states, derive drift/fitness/risk evidence, and generate non-authoritative Mermaid views.

## Components and boundaries

- Architecture model/rules: target-owned untrusted data.
- Local loader/diff/fitness/diagram modules: advisory preflight implementation.
- M1 spec/receipts: preserved intent and evidence authority, extended only with current architecture bindings.
- M2-B: separate independently implemented Trust CI enforcement task.

## Data flow

Canonical system/rules + schema/contract inventories + exact base/head paths -> validation/digests -> architecture diff/drift -> mandatory fitness/applicability -> monotonic risk -> local verification/receipts. Later M2-B recomputes the critical floor independently from exact checkout bytes.

## API and event contracts

M2-A freezes machine-readable baselines for existing Trust CI HTTP endpoints, approval/attestation envelopes, and the bounded GitHub pull-request projection. It changes no runtime API and treats unsupported compatibility semantics as blocking.

## Decisions

- Freeze `25bfbe59ea188d9687b20a9caad19e7db3d031f8` as the one adoption base; never rewrite route history.
- Split M2-A product work from M2-B `trust-ci/**` work.
- Use two strict root schemas and canonical JSON text without new dependencies.
- Use explicit directed capability edges and one structured `failure_behavior` per edge.
- Install code/schema/templates only; never install or overwrite target-owned architecture authority.

## Risks and mitigations

- Self-certification: M2-A remains advisory; M2-B duplicates the critical external floor.
- Overclaiming analysis: unsupported applicable semantics fail closed.
- False non-applicability: every result carries predicate, scan inventory, matches, and digest.
- Baseline contamination: exact architecture diff always uses the frozen completed-M1 adoption SHA.
- Scope mixing: M2-A fails if any `trust-ci/**` path changes.

# Architecture — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Prior behavior

Architecture authority was absent. README's complete K16 graph is intentionally non-directional and cannot prove dependencies, trust, secrets, protocols, data classifications, failure contracts, or compatibility.

## Implemented M2-A behavior

Two strict JSON-compatible YAML documents are architecture authority after explicit target adoption. Dependency-free modules validate and normalize them, compute stable digests, compare exact states, derive drift/fitness/risk evidence, and generate five non-authoritative Mermaid text views. Canonical `architecture/adoption.json` is the durable adoption switch, not semantic model authority.

## Components and boundaries

- Architecture model/rules: target-owned untrusted data.
- Adoption marker: strict target-owned durable state; absent means legacy `not_configured`, present means missing/invalid model files fail closed.
- Local loader/diff/fitness/diagram modules: advisory preflight implementation.
- M1 spec/receipts: preserved intent and evidence authority, extended only with current architecture bindings.
- M2-B: separate independently implemented Trust CI enforcement task.

## Data flow

Canonical marker + system/rules + schema/contract inventories + exact base/head paths -> validation/digests -> architecture diff/drift -> mandatory fitness/applicability -> monotonic risk -> local verification/receipts. Later M2-B recomputes the critical floor independently from exact checkout bytes.

## API and event contracts

M2-A freezes machine-readable baselines for existing Trust CI HTTP endpoints, approval/attestation envelopes, and the bounded GitHub pull-request projection. It changes no runtime API and treats unsupported compatibility semantics as blocking.

## Decisions

- Freeze `25bfbe59ea188d9687b20a9caad19e7db3d031f8` as the one adoption base; never rewrite route history.
- Split M2-A product work from M2-B `trust-ci/**` work.
- Use two strict root schemas and canonical JSON text without new dependencies.
- Use explicit directed capability edges and one structured `failure_behavior` per edge.
- Install code/schema/templates only; never install or overwrite target-owned architecture authority.
- Treat examples as non-authoritative and require manual marker creation only after both target documents are reviewed.

## Risks and mitigations

- Self-certification: M2-A remains advisory; M2-B duplicates the critical external floor.
- Overclaiming analysis: unsupported applicable semantics fail closed.
- False non-applicability: every result carries predicate, scan inventory, matches, and digest.
- Baseline contamination: exact architecture diff always uses the frozen completed-M1 adoption SHA.
- Scope mixing: M2-A fails if any `trust-ci/**` path changes.

## Reproducible operator surfaces

- Authority: `architecture/adoption.json`, `architecture/system.yaml`, `architecture/rules.yaml`.
- Schemas: `schemas/architecture-system.schema.json`, `schemas/architecture-rules.schema.json`.
- CLI: `scripts/grok_architecture.py` (`validate`, `summary`, `drift`, `diagram`, `diff`, `fitness`).
- Generated projections: `architecture/generated/{context,container,deployment,data-flow,trust-boundary}.mmd`.
- Local verification: `python3 scripts/grok_verify.py --mode pr --no-record --json`.

Worktree verification selects its architecture comparison base through verification policy; receipt construction independently binds its configured architecture fields. Final review must compare those paths on the final tree before claiming identical base selection. No M2-A documentation treats local receipts, projections, or Markdown as authority.

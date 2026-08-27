# Architecture — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Prior behavior

Architecture authority was absent. README's complete K16 graph is intentionally non-directional and cannot prove dependencies, trust, secrets, protocols, data classifications, failure contracts, or compatibility.

## Implemented M2-A behavior

Two strict JSON-compatible YAML documents are architecture authority after explicit target adoption. Dependency-free modules validate and normalize them, compute stable digests, compare exact states, derive drift/fitness/risk evidence, and generate five non-authoritative Mermaid text views. Canonical `architecture/adoption.json` is the durable adoption switch, not semantic model authority. Queue applicability uses a package-aware bounded abstract interpreter with monotone joins, and installer mutation is limited to atomic publication at an absent new target.

## Components and boundaries

- Architecture model/rules: target-owned untrusted data.
- Adoption marker: strict target-owned durable state; absent means legacy `not_configured`, present means missing/invalid model files fail closed.
- Local loader/diff/fitness/diagram modules: advisory preflight implementation; diagram operations are render/check-only and have no repository mutation capability.
- Queue provenance: one bounded abstract-interpreter result drives both background-job fitness and `new_queue` risk; relevant uncertainty fails closed without tainting unrelated operations.
- Installer: existing repositories are read-only planning inputs; a complete payload may be staged and published only to an absent target on Linux with descriptor-relative `O_NOFOLLOW`/`O_DIRECTORY` operations and libc/filesystem support for `renameat2(RENAME_NOREPLACE)`.
- M1 spec/receipts: preserved intent and evidence authority, extended only with current architecture bindings.
- M2-B: separate independently implemented Trust CI enforcement task.

## Data flow

Canonical marker + system/rules + schema/contract inventories + exact base/head paths -> validation/digests -> architecture diff/drift -> bounded queue provenance and mandatory fitness/applicability -> monotonic risk -> local verification/receipts. Separately, source payload -> deterministic read-only install plan -> verified sibling stage -> absent-target no-replace publication. Later M2-B recomputes the critical floor independently from exact checkout bytes.

## API and event contracts

M2-A freezes machine-readable baselines for existing Trust CI HTTP endpoints, approval/attestation envelopes, and the bounded GitHub pull-request projection. It changes no runtime API and treats unsupported compatibility semantics as blocking.

## Decisions

- Freeze `25bfbe59ea188d9687b20a9caad19e7db3d031f8` as the one adoption base; never rewrite route history.
- Split M2-A product work from M2-B `trust-ci/**` work.
- Use two strict root schemas and canonical JSON text without new dependencies.
- Use explicit directed capability edges and one structured `failure_behavior` per edge.
- Plan existing consumers read-only; materialize code/schema/templates only into an absent new target; never install or overwrite target-owned architecture authority.
- Emit dependency commands as advice only, reject `--force`, and require existing-consumer updates to use a normal reviewed source-change workflow.
- Treat examples as non-authoritative and require manual marker creation only after both target documents are reviewed.
- Keep projection generation read-only; checked-in Mermaid updates are normal reviewed source edits.
- Resolve queue adapters with Python package semantics and one fail-closed provenance result shared by fitness applicability and risk.

## Risks and mitigations

- Self-certification: M2-A remains advisory; M2-B duplicates the critical external floor.
- Overclaiming analysis: unsupported applicable semantics fail closed.
- False non-applicability: every result carries predicate, scan inventory, matches, and digest.
- Baseline contamination: exact architecture diff always uses the frozen completed-M1 adoption SHA.
- Scope mixing: M2-A fails if any `trust-ci/**` path changes.
- Cleanup ambiguity: ownership is bound from the original descriptor; if constructor identity cannot be proved, preserve the unresolved entry and report `manual cleanup required: installer ownership is unresolved` rather than deleting a possible replacement.

## Reproducible operator surfaces

- Authority: `architecture/adoption.json`, `architecture/system.yaml`, `architecture/rules.yaml`.
- Repository-path ownership uses a unique longest-prefix rule; exact/equal-specificity ownership ties are invalid. Shared `trust-ci/compose.yaml` configuration has one source owner and describes runtime nodes through their explicit relationships.
- Schemas: `schemas/architecture-system.schema.json`, `schemas/architecture-rules.schema.json`.
- CLI: `scripts/grok_architecture.py` (`validate`, `summary`, `drift`, `diagram`, `diff`, `fitness`).
- Installer: `scripts/install_into.py --plan TARGET` for existing/absent inspection and `scripts/install_into.py --materialize-new TARGET` only for absent-target publication. Materialization requires Linux descriptor-relative `O_NOFOLLOW`/`O_DIRECTORY` operations and libc/filesystem support for `renameat2(RENAME_NOREPLACE)`; an unavailable/unsupported capability fails closed without publication, with no fallback. The supported alternative is `--plan` plus a normal reviewed source-change. `--force` is rejected.
- Generated projections: `architecture/generated/{context,container,deployment,data-flow,trust-boundary}.mmd`.
- Local verification: `python3 scripts/grok_verify.py --mode pr --no-record --json`.

Worktree verification selects its architecture comparison base through verification policy; receipt construction independently binds its configured architecture fields. Final review must compare those paths on the final tree before claiming identical base selection. No M2-A documentation treats local receipts, projections, or Markdown as authority.

# Requirements — land workflow artifact adapters with latest-upstream version contract

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: Given the delivered head, when the adapter module, CLI, three schemas, three test suites and both epic documents are looked up, then all exist and every shipped path appears in installer/manifest inventories (tests/test_workflow_artifacts*.py, tests/test_installer.py, tests/test_manifest_package.py).
- [ ] AC-002: Given upstream tags v6.3.0/v6.12.0/v1.0.7, when `tests/test_workflow_sources.py` runs, then ids equal the schema `source_type` enum, each pinned version has a loadable unmodified-shape parser test, README rows match config, observation is fresh (≤90 days), and no third-party tree content exists outside declared prefixes.
- [ ] AC-003: Given main's shared-memory documents, when the PR diff is inspected, then only additions appear (10 decisions + 15 mistakes entries; governance projection blocks byte-identical; zero removed headings).
- [ ] AC-004: Given the post-delivery state model, when `tests/test_project_state.py` runs, then `observed_main_sha` equals `b6fe340…` (PR #91), the runtime evidence is a live re-observation naming that base, and START_HERE/README carry the same sha.
- [ ] AC-005: `grok_verify --mode pr` (runner-equivalent capability) green on the final clean tree; code/test/security receipts recorded against that fingerprint.
- [ ] AC-006: PR-only delivery; merge only after `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS on the exact head.

## Failure and edge cases

- Historical packages without `workflow/manifest.json` must SKIP the new verification check (covered by `WorkflowArtifactsVerificationTests`).
- Upstream format audit DID find drift (BMAD heading levels/status carriers; spec-kit emphasis false-positive in the guard): corrected in this change with verbatim-shape tests, rulings for rejected items in `evidence/upstream-format-spot-check-2026-09-15.md`.
- Rebase onto a newer main (happened once: #91) → architecture appends and generated projections re-derived, never hand-merged.

## Governance context

No governance rule, example or debt record is created, altered or referenced as authority by this change. Candidate-only boundary of the adapters is asserted by INV-001 tests.

- Applicable rule IDs: none.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: none.

## Non-functional requirements

- Security: descriptor-bound no-follow bounded loading; closed command policy for RED/GREEN metadata; no network/subprocess/LLM in the compiler; no secrets (FORBID-003).
- Reliability: gate runtime unchanged for packages without manifests; deterministic digests; CAS rollback/recovery semantics ported intact.
- Performance: 46 adapter tests run in <0.4 s; verification adds one file-existence-gated check.
- Observability: SIG-001 — `grok_artifacts.py validate` output on the ported d41aa6 package (evidence/sig-001-d41aa6-validate.json).

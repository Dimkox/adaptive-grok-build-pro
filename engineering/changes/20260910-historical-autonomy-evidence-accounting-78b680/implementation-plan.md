# Historical Evidence Accounting Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development with the route-selected ai_implementer as the sole application-code owner.

**Goal:** Account for existing delivery and missing autonomy evidence without inventing task acceptance or permissions.
**Architecture:** Pure local preflight validation/accounting plus a thin explicit-file CLI; separately collected private snapshots remain outside the public repository.
**Tech Stack:** Python 3 standard library, unittest, existing installer and quality gates.
**Spec:** requirements.md, architecture.md and evidence/analysis-architect.md in this change package.

## Global constraints

No network, provider invocation, database, new dependency, external mutation, current-parameter backfill or runtime activation. No consumer identifiers, URLs, source SHA or business content in committed material. Local report is untrusted imported evidence, not M8 qualification or external attestation. Keep existing authority ceiling and factory contracts unchanged.

## Task 1: Pure accounting and input validation

Files: create .grok-stack/adaptive_grok/history.py and tests/test_history.py.
Interfaces: HistoryError, load_history(path), summarize_history(data). Follow architect report's version-1 input shape with these required additions: PR base_ref and merged_at nullable; repository task_inventory_complete Boolean; task intervention_source_refs plus nullable session_started_at/session_ended_at. Complete measured sessions require source reference and valid bounded start/end, partial requires measurement source, unknown must have null count.

- [x] Add a minimal synthetic repository factory with empty tasks and explicit pagination_complete=true/task_inventory_complete=false.
- [x] Add regressions: a merged PR alone gives merged_prs_observed=1 while accepted_task_total remains null; actor User gives no intervention count; identical PR replay counts once; conflicting same-identity observations raise HistoryError; incomplete pagination remains incomplete.
- [x] Run python3 -m unittest tests.test_history and preserve expected failing output before implementation.
- [x] Implement closed bounded input validation, duplicate-key/nonfinite/Boolean-count rejection, canonical ordering/dedup, per-repository PR observations and independent task records. Read only the explicit regular input file with a finite size limit; do not follow source_refs.
- [x] Extend tests and implementation for many-to-many PR/task mappings, unknown metrics versus measured zero, partial/complete intervention coverage, unsupported task class, sparse profile missing fields, repository/profile mismatch, changed profile separation and deterministic input digest.
- [x] Add 30 synthetic claimed acceptances with a full profile; arithmetic may report observed accounting floor but m8_qualification stays not_evaluated, authority_effect stays none. Unsupported/expired profile metadata must not be presented as eligible qualification. No current factory profile parser import is required if report labels profile completeness as metadata coverage only and validates field shapes; don't create a new architecture edge.
- [x] Focused tests pass. Task totals must label observed records and unknown full-history count separately when task_inventory_complete=false.

## Task 2: CLI and consumer delivery

Files: create scripts/grok_history.py; modify scripts/install_into.py MANAGED_FILES and .grok-stack/config/managed.json scripts; extend relevant installer test and tests/test_history.py.

- [x] Write failing subprocess CLI tests for a synthetic input and invalid input; no actual GitHub/provider requests.
- [x] Implement python3 scripts/grok_history.py SNAPSHOT with JSON stdout and bounded safe stderr/exit failure. No repository discovery, implicit scans, output file mutation, subprocess or network in utility code.
- [x] Enroll installed CLI and prove its help works from an installed consumer tree.
- [x] Run focused tests and relevant existing installer tests.

## Task 3: Operator instructions and final verification

Files: create engineering/runbooks/historical-autonomy-evidence.md and one synthetic example under examples/historical-evidence/; minimally link from README.md; update this change's implementation/test evidence.

- [x] Explain explicit snapshot capture, default/delivery refs, classification of branch synchronization, source provenance, task acceptance versus PR merges, partial intervention lower bounds, unknown coverage and exact-profile accounting limits.
- [x] Explain keeping private snapshots/reports outside a public checkout; source references are opaque and not fetched by the CLI.
- [x] Document concrete next capability order: contemporaneous task/run/profile instrumentation, durable M7 acceptance/currentness with exact-SHA external evidence, per-profile cohort/audits, separately authorized activation and recovery.
- [x] Return changed files and precise focused test results to root. Root generates the private case input/report, runs full grok_verify and selected independent reviews, records final receipts and handles delivery authority.

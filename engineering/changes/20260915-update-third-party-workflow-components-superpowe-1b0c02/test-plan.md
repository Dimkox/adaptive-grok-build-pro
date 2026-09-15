# Test plan — adapter port and version contract

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Imported framework documents can never mint route/receipt/approval/governance authority | `tests/test_workflow_artifacts_adversarial.py` (CanonicalReceiptTests, CommandAuthorityTests, RuntimeParityTests) |
| P0 | Loader fail-closed set: path escape, symlinks/FIFOs, non-NFC, duplicate keys, YAML authority syntax, limits | `tests/test_workflow_artifacts.py` (WorkflowSourceTests) |
| P0 | Deterministic graph/report digests; stale stored artifacts fail verification; historical packages skip | `tests/test_workflow_artifacts.py` (WorkflowConvergenceTests), `tests/test_verification_doctor.py::WorkflowArtifactsVerificationTests`, `tests/test_workflow_artifacts_cli.py` |
| P0 | CAS publication: serialized writers, rollback before displaced-content read, competitor preservation, recovery names, no-unlink | `tests/test_workflow_artifacts_adversarial.py` (SerializedCasTests) |
| P1 | Version contract: config ids == schema enum; pins semver/current; named shape tests load and pass; README==config; ≤90-day observation; no vendored trees | `tests/test_workflow_sources.py` |
| P1 | Registration: installer payload sorted/complete; root entries incl. `.specify`; architecture contracts floor + workflow id-set; projections fresh | `tests/test_installer.py`, `tests/test_structure.py`, `tests/test_architecture_model.py`, `grok_architecture.py diagram --check` |
| P1 | Shared-memory union without clobber; state model self-consistent post-observation | `git diff` review, `tests/test_project_state.py`, `tests/test_governance.py` |
| P2 | End-to-end dogfood: stored 2026-08-30 graph/report revalidate on the new tree | `evidence/sig-001-d41aa6-validate.json` (rc=0, 0 findings) |

## Automated checks

- Unit: full `unittest discover -s tests` via `python3 scripts/grok_verify.py --mode pr` (GROK_VERIFY_CAPABILITY=repository-sandbox).
- Integration: verification check wiring + receipts hardening blast radius (`tests/test_change_receipts.py`, `tests/test_hooks.py`, `tests/test_verification_doctor.py`).
- Contract: three workflow JSON Schemas compiled through the architecture model (`tests/test_governance.py` widened tuple).
- E2E: CLI read-only validate on the ported package (SIG-001).
- Static analysis: Ruff + Bandit over changed Python surfaces inside the gate.

## Manual checks

- Diff-shape audits: system.yaml +185/−0; docs appends +N/−0; mmd +N/−0; no `## Unreleased` heading.
- `git log -p` scan confirming governance projection blocks untouched.

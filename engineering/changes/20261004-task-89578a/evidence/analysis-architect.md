# Architect — read-only analysis

Source HEAD ee3911869419204154e02900e58bf31492ee744c remained unchanged. Private capacity snapshot .review-scratch/fast-architect-capacity-20261004T195638Z.md. No tests or candidate edits.

Recommend default PR/release fail-fast at completed-check boundaries with explicit --keep-going diagnostics. Preserve safety preflight refusals even in diagnostics. Existing orchestration verification.py:2161 and nested _python_checks1742 need the same minimal recording/refusal helper. Retain actual result first; skip allowances stay closed at quality_gates.py:64.

Refusal jumps to existing source-stability/QG/report finalizer verification.py:2201, never directly returns. Remaining selected checks use explicit SKIP/not-executed, distinguishable from scope omissions. Successful inventory/selector unchanged.

Universal FAIL receipts are incompatible: current spec/architecture/governance binding rederivation at receipts.py:791; invalid governance653 and preflight2131 deliberately refuse. Keep explicit not_recorded for invalid authority, normal current FAIL only for stable bindable cases. Source mutation/publication errors never PASS.

Existing fast still discovers Core verification.py:1823 and cannot promise180s. Named smoke reuses Core environment python_test_runner.py:290 and timeout/process ownership; --no-record, explicit targets and clean committedHEAD; cannot qualify PR.

Existing architecture ownership system.yaml:1962/2009 and governed rules.yaml:42 already cover modules. No expansion/service/dependency.

Acceptance: actual primary failure+unexecuted names; source-stability/finalQG retained; keep-going cannot bypass safety; valid FAIL versus invalid recording refusal explicit; successful full inventory unchanged; committedHEAD smoke<=180s; independent reviews return complete reports before final freeze.

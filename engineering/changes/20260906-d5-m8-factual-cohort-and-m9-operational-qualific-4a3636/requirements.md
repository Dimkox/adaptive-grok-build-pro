# Requirements — D5 qualification accounting

## Acceptance criteria

- [ ] AC-A1: Successor branch ancestors `fd51dcfed6b33f4a8707c0db602328146df17cc9` and is not `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] AC-A2: Product diff vs `origin/main` is limited to factory/delivery library + tests + this package + short `decisions.md` append. No `VERSION`, packages ZIP, `.github/workflows/`, SQL `019`, `policy.py`, compose, PR #12 CLI.
- [ ] AC-B1: Missing ledger and empty ledger both report `factual_accepted_task_count = 0`.
- [ ] AC-B2: Synthetic 30-row `valid_cohort_payload()` / `SYNTHETIC_ALGORITHM_FIXTURES_ONLY` does not increment factual count; `evaluate_activation(...).activated is False`.
- [ ] AC-B3: `append_factual_acceptance` rejects `synthetic_forbidden`, `m7_acceptance_missing`, `m7_currentness_missing` (and does not write a row).
- [ ] AC-B4: Mutating any `AutonomyTupleV1` component opens a new empty cohort (count 0), never copies records.
- [ ] AC-B5: `evaluate_activation` constants: `separate_activation_required=True`, `external_action_authorized=False`, `auto_merge_authorized=False`, `authority_ceiling=L2`. Empty main reasons include `empty_cohort` / `insufficient_acceptances` / `m7_acceptance_missing` / `m7_currentness_missing` / `activation_record_missing`.
- [ ] AC-C1: `evaluate_m9_operational_qualification` is false with blockers for signed input, sealed in-memory adapter, unexercised recovery, missing production authority, and `m8_not_activated`.
- [ ] AC-C2: `DryRunController` / `FakeEnvironmentAdapter` behavior unchanged; production still unreachable.
- [ ] AC-D1: Deadline evaluation after `2026-09-08T00:00:00+03:00` still has `calendar_deadline_waives_gates=false`.
- [ ] AC-E1: No test asserts `activated is True` or `qualified is True` for operational M9.
- [ ] AC-F1: `python3 scripts/grok_verify.py --mode pr` PASS. VERSION remains `2.0.15`.

## Failure and edge cases

- Implementing on 2.0.12 → hard fail.
- Counting synthetics toward 30 → hard fail.
- Flipping M7 availability booleans → hard fail.
- Wiring qualification into `DryRunController` so synthetic delivery tests break → hard fail.

## Non-functional

- Security: stay library-only; this route has no security_reviewer.
- Compatibility: existing M8/M9 algorithms and synthetic tests stay green.

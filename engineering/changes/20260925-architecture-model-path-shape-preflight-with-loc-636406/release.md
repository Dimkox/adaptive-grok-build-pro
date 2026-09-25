# Release plan — architecture model path-shape preflight with located diagnostics

## Deployment

Ships inside the `.grok-stack` stack; no service, image or migration is rebuilt. Consumers pick it up
on the next stack install: `scripts/install_into.py` syncs the whole `.grok-stack` tree except
`.grok-stack/runtime/`, so `adaptive_grok/architecture.py` and `adaptive_grok/doctor.py` travel with it.

## Feature flags / staged rollout

No flag. The change is diagnosis-only: the accepted and rejected value sets are identical, so nothing
that loaded before stops loading. Rollout is the ordinary PR-then-Trust-CI path for this repository.

## Metrics and alerts

- `SIG-001`: `scripts/grok_doctor.py` prints one `architecture-model` line — `pass` on a valid model,
  `fail` plus the located `document:line`, owning id, quoted value and reason on an invalid one.
- `SIG-002`: `preflight_architecture()` finding count is 1 for the injected defect and 0 for the
  repaired model (pinned by `tests/test_architecture_model_preflight.py`).
- Time-to-diagnosis is the operational signal: seconds for the doctor line instead of a ~453 s root
  suite that reported 40 unlocated errors.

## Go/no-go criteria

Go when: `tests/test_architecture_model_preflight.py` is green; the neighbouring architecture,
governance, receipt, structure and doctor suites are green; `ruff` and `git diff --check` are clean;
one `python3 scripts/grok_verify.py --mode pr` run passes; and `architecture/system.yaml`,
`architecture/rules.yaml` and `architecture/generated/` show no diff. No-go if any of those move —
in particular if the shipped model's digests change.

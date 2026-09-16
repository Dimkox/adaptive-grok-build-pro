# Test plan — qwen-omni-intl profile and probe classification

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Intl omni profile: host, model, streaming, five media, distinct digest | `test_international_omni_profile_is_streaming_and_five_media` |
| P0 | Probe failure prints only bounded enums, never credential or body | `test_probe_cli_reports_authentication_class_without_the_body`, `test_probe_cli_failure_never_prints_exception_or_credential` |
| P1 | Env composition admits both omni names, still refuses unknown | `test_environment_composition_accepts_both_omni_profiles` |
| P1 | Host config and server acceptances extended | `factory/tests/test_landing_host.py`, `factory/tests/test_landing_server.py` |
| P0 | Capability claim backed by a live request | `evidence/live-omni-probe.md` and the outputs quoted in `brief.md` |

## Automated checks

- `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live_executors factory.tests.test_landing_host factory.tests.test_landing_server factory.tests.test_landing_provider` → 107 tests OK (adds capability-contract fact-shape guard — the enum itself is frozen by issue #104 — classification clamping, enumeration-subset and failover-exclusion tests)
- `python3 -m unittest discover -s tests` and `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- Confirm no credential appears in `git diff` (`grep -c` for the key name in added lines).
- Confirm `PROVIDER_ORDER` and the mainland omni binding are untouched.

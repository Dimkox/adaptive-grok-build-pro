# Test plan — lazy Trust CI CLI imports on 2.0.15

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Characterization: current eager `cli.py` `--help` fails when FastAPI is blocked | failing test first |
| P0 | `--help`, `approval-create --help`, `approval-submit --help` succeed with server graph + cryptography blocked (fresh subprocess, sitecustomize) | `trust-ci/tests/test_cli.py` |
| P0 | `approval-submit` posts exact fixture bytes to loopback `/approvals` with frozen User-Agent, cryptography still blocked | same |
| P0 | Importing `cli` does not load server modules | same |
| P0 | 17 non-human commands: only that branch's slice loads; mocked safe effect; `keygen` writes no PEM | same |
| P0 | `approval-create` fake-module path: mocked Policy/Signer/sign/`_write_new_json`; no key file | same |
| P1 | Unmodified `test_policy.py` path/glob/UTF-8 cases still pass | existing suite |
| P1 | Unmodified holdout + signing tests still pass | existing suite |
| P1 | README uses `python -m adaptive_trust_ci.cli`, current envelope field names, placeholder paths only | review |

Do **not** copy PR #12 `test_approval_create_runs_without_server_imports_and_preserves_envelope_contract` (it calls `Signer.generate()`). Existing `trust-ci/tests/test_signing.py` covers envelopes.

## Automated checks

- Unit: new `trust-ci/tests/test_cli.py` plus existing Trust CI unit tests.
- Integration: none new; no live Postgres/API.
- Contract: envelope/HTTP unchanged; submit fixture is not a signed operational envelope and is not sent to a deployed URL.
- E2E: none.
- Static analysis: `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- None required for this slice. Do not run `approval-create` against a human key path.

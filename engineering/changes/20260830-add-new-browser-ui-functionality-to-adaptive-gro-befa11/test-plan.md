# Test plan — Add new browser UI functionality to Adaptive Grok Build Pro: create a one-command local HTTP demo application with a polished responsive dashboard using real repository routing, typed-spec, architecture, governance, and verification-summary logic against bundled sample data; add automated tests and user documentation. Do not perform external writes.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Real adapters equal direct calls and mutate no state | `tests/test_demo.py` |
| P0 | Closed HTTP API, security controls, headers, and safe failures | `tests/test_demo_http.py` |
| P0 | Installer, architecture, OpenAPI, and package consistency | existing installer/architecture/structure suites |
| P1 | Responsive/accessibility/offline UI and safe DOM | structural tests; optional browser evidence |

## Automated checks

- Unit: `python3 -m unittest tests.test_demo -v`
- Integration: `python3 -m unittest tests.test_demo_http -v`
- Contract: OpenAPI and endpoint/direct-call equivalence.
- E2E: ephemeral loopback walkthrough; optional 360px/1440px browser evidence.
- Static analysis: architecture/installer/structure suites, then `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- Five-minute investor walkthrough plus stop/restart stale recovery.
- Keyboard-only skip link, prompt, submit, result, retry, evidence path.

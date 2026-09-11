# Test plan — retract ChatGPT webhook URL

| ID | Case | How |
| --- | --- | --- |
| P0 | Operator docs do not present ChatGPT URL or hostname as live webhook/TLS | `test_operator_docs_do_not_present_chatgpt_webhook_as_live` in `trust-ci/tests/test_m0_invariants.py`. Red on `decisions.md` before retraction; green after. |
| P0 | Existing M0 invariants stay green | `python3 -m unittest trust-ci.tests.test_m0_invariants` |
| P0 | HMAC contract unchanged | Do not edit `test_webhooks_github.py` / `test_api.py`; existing suite still passes under `grok_verify --mode pr`. |
| P1 | No live probe of the ChatGPT URL | Characterization is string scan of tracked docs, not HTTP. |

No public unsigned POST. No GitHub hook API. No PEM.

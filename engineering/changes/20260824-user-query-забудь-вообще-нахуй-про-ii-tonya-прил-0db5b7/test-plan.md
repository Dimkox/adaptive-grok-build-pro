# Test plan

| ID | Case | How |
| --- | --- | --- |
| P0 | Five operator docs have no `ii-tonya` | Expand `test_operator_docs_do_not_present_chatgpt_webhook_as_live` |
| P0 | `decisions.md` names the GitHub App URL | New assert in M0 invariants |
| P0 | `mistakes.md` does not say nginx-as-app | New assert in M0 invariants |
| P0 | Existing M0 suite stays green | `python3 -m unittest trust-ci.tests.test_m0_invariants` |
| P1 | No live HTTP probe of that public domain | String scan only |

HMAC tests are not rewritten.

# Implementation — retract ChatGPT webhook URL

Route `b66b867ba5ab`. Change `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`.

Write owner `integration_implementer` could not spawn: hook denied `Another write agent is already active: ['general_implementer']` (`01a03333-2d98-7de1-a851-7e96dfec7e62` stale in `.grok-stack/runtime/agent-state.json` since 2026-08-24T09:56:27). Clearing that lock is a protected-path write not in this grant. Parent executed the approved retraction.

No GET/POST of `https://trust-ci.ii-tonya.ru/webhooks/github`. No GitHub App hook API. No PEM/secret reads. No Apache/DNS/certbot. No FastAPI change.

## Changed files

| File | Change |
| --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | `test_operator_docs_do_not_present_chatgpt_webhook_as_live` |
| `decisions.md` | ChatGPT hostname void; Apache leftover without that hostname |
| `mistakes.md` | Root cause: ChatGPT hostname treated as operator truth |
| `engineering/changes/…cec0c7/brief.md` | One-line retraction banner |
| `engineering/changes/…010964/brief.md` | One-line retraction banner |

## Commands

```
python3 -m unittest trust-ci.tests.test_m0_invariants
# 9 tests OK
```

Pre-change `decisions.md` contained `trust-ci.ii-tonya.ru`; the new test would fail on that tree. Atomic protected-path batch applied test + retraction together.

## Residual risk

- Host Apache leftover vhost still exists; user ordered `не трогаем`.
- GitHub App webhook URL was never set (JWT/PEM forbidden). Do not set it to the ChatGPT URL.
- Public GitHub delivery still absent. Loopback HMAC remains the only proven path. M0.2 webhook **not done**.
- Stale `general_implementer` in agent-state still blocks future write-agent spawn.

## Rollback

Revert the docs/test commit. No host rollback.

# Architecture — retract ChatGPT webhook URL

No HTTP, event, or env contract change. Producer/adapter/consumer stay frozen.

```
[producer — frozen]
  ONLY proven: loopback HMAC POST http://127.0.0.1:18080/webhooks/github
  FORBIDDEN: GitHub App URL https://trust-ci.ii-tonya.ru/webhooks/github
  FORBIDDEN: repository webhook

        │  X-Hub-Signature-256, X-GitHub-Event
        ▼
[adapter — frozen]
  api.py POST /webhooks/github → HMAC → parse_pull_request_event
        ▼
[consumer — frozen]
  PostgresStore.enqueue / cancel_pr
        ▼
[publisher — frozen]
  worker GitHubAppAuth → Check Runs (not hook config)
```

`TRUST_CI_PUBLIC_BASE_URL` stays loopback HTTP. Host Apache leftover vhost is not part of the product contract and is not modified (`не трогаем`).

Sibling `cec0c7` operator mapping that named the ChatGPT URL is void. This slice updates operator memory (`decisions.md`, `mistakes.md`) and a characterization test only.

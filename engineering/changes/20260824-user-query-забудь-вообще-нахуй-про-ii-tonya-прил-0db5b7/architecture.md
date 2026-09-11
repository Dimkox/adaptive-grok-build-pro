# Architecture — GitHub App identity

No HTTP/event/env contract change.

```
[application]
  GitHub App https://github.com/apps/adaptive-trust-ci
  slug adaptive-trust-ci  App ID 4694114  Installation 156003193
  webhook config lives on that App registration (operator UI later)
        │
        │  NOT this slice: GitHub delivery to a public URL
        ▼
[proven intake — frozen]
  loopback HMAC POST http://127.0.0.1:18080/webhooks/github
        ▼
[adapter/consumer — frozen]
  FastAPI POST /webhooks/github → HMAC → enqueue
        ▼
[publisher — frozen]
  worker Check Runs owned by that App
```

A public website is not the application. Do not invent a replacement public webhook URL.

# Requirements

## Agent cannot claim done until

- GitHub App hook URL is HTTPS `…/webhooks/github` with SSL verification on
- Event `pull_request` subscribed
- Unsigned public POST returns **401** from FastAPI (not 405 nginx, not SSL error)
- Repo `/hooks` stays empty

## This slice (no write owner)

- Do not read PEM or print `TRUST_CI_WEBHOOK_SECRET`
- Do not create repository webhook
- Record that App hook API is JWT-only

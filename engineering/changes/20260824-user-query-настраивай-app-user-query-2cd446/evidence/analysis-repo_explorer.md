# repo_explorer — GitHub App visibility (read-only)

Route: `2cd446440734`  
Change: `20260824-user-query-настраивай-app-user-query-2cd446`  
App (from user context, not fetched): ID `4694114`, install `156003193`  
Public webhook URL (not applied): `https://claw.taild9f611.ts.net/webhooks/github`

Constraints honored: no PEM, no `.env`, no webhook secret, no repository webhook create, no PATCH.

## `gh api /app`

HTTP **401**. Body: `A JSON web token could not be decoded`.

The current `gh` credential is **not** an App JWT. User/OAuth installation tokens cannot call `/app`.

## `gh api /app/hook/config`

HTTP **401**. Same JWT decode error.

App webhook config is **not** visible or writable with this token. JWT is required to GET/PATCH `/app/hook/config`.

## `gh api repos/Dimkox/adaptive-grok-build-pro/hooks`

HTTP **200**. Body: **`[]`** (empty array).

The token **can** list repository hooks. There are **no** repo-level webhooks. Do not create one; App delivery is App hook config, not a repo hook.

## Funnel (read-only)

`sudo -n tailscale funnel status` succeeded.

Funnel is **up**:

- `https://claw.taild9f611.ts.net` (Funnel on)
- `/webhooks/github` → `http://10.200.200.1:18080/webhooks/github`

Public URL matches the intended App webhook path.

## Answers

| Question | Result |
|---|---|
| JWT required for `/app` and `/app/hook/config`? | **Yes.** Current token: 401 JWT decode. |
| Repo hooks empty? | **Yes.** `[]` |
| Funnel still up? | **Yes.** Path `/webhooks/github` proxied. |

Next (not done here): generate App JWT from a human-held PEM **outside** this agent, then GET `/app/hook/config` and PATCH only after explicit approval. Do not use this `gh` session as App auth.

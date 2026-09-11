# Architecture

App webhook and repo webhook share Trust CI `POST /webhooks/github` HMAC. Installation token cannot publish App hook config. Only App JWT (PEM) or the App settings UI can.

Events: `pull_request` covers opened/synchronize/reopened/closed; drafts already enqueue. `ping` after valid HMAC is 200 `ignored-event`.

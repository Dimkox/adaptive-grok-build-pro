# Security boundary

## In scope

Security reports are relevant when the skill could execute instructions from
retrieved content, expose secrets, write outside the selected project, bypass the
audit-only no-write contract, interpolate unsafe values into generated markup,
or perform an external or production mutation without exact authorization.

SEO recommendations, ranking uncertainty, and an unavailable third-party
validator are quality limitations unless they also cross a security boundary.

## Safe reporting

Use a verified maintainer contact or another private channel that the repository
currently publishes. If no private route is available, do not post exploit code,
secrets, customer content, or operational details in a public issue; submit only
a minimal request for a private contact through the repository's public issue
tracker or a maintainer's verified public profile.

Include the affected commit, mode, minimal reproduction, impact, and whether any
external system or sensitive data was touched. Redact tokens, private URLs,
personal data, proprietary page content, and credential material.

## Agent response boundary

Codex may inspect repository-local public source needed to reproduce the issue,
but must not read `.env`, credentials, private keys, secret stores, production
dumps, or unrelated customer files. Reproduction must remain local and read-only
unless the user separately authorizes exact write targets; do not deploy, submit
forms, probe third-party systems, or publish vulnerability details as part of
triage.

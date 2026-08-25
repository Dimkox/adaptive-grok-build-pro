# Architecture

See `evidence/analysis-architect.md`. Binding: host is **claw**. Do not bind host 8080. Publish `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. Compose project `adaptive-trust-ci`. Outbound GitHub via app-stack `proxy-gateway` `127.0.0.1:1080`. No compose-up this slice.

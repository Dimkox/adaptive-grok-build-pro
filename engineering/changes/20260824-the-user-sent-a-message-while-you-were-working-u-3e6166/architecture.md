# Architecture

Authority: `evidence/analysis-architect.md`.

**Pick: host-only overlay. Do not edit product `trust-ci/compose.yaml`.** `docker-engine` stays in the tracked file unused. Tests are not updated.

Overlay path: `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode 0600. Mount `/var/run/docker.sock` on worker and runner-loader only. `DOCKER_HOST=unix:///var/run/docker.sock`. `extra_hosts: host.docker.internal:host-gateway`. `group_add` host docker GID. Bind-replace workspaces/holdout with host paths (`!override`).

Runner isolation remains argv policy in `sandbox.py`: no socket, `network=none`, no token, no key.

Local HMAC POST is a loopback characterization of the existing `/webhooks/github` contract, not GitHub webhook registration.

Residual: worker+PEM+host socket on the same engine as SearXNG/n8n is host-root equivalent; user already accepted claw as CI host. If `host-gateway` cannot reach glider `:1080`, host socat fallback — do not rebind glider or `network_mode: host`.

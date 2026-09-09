# Remediation-5 final local pinned-runner evidence

## Result

- Disposable exact-tree test commit: `ec341a22874872e50b2e73f05e6934c816f6fcc6`.
- Test result: **404/404 PASS**.
- Duration: **230.283 seconds**.
- Runner image: `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`.

## Exact execution contract

- Container identity: UID/GID `10001:10001`.
- Source: a clean disposable Git checkout of the exact commit with normal checkout read modes and executable bits preserved.
- Working tree mount: `/workspace:ro`.
- Git metadata mount: `/workspace/.git:ro`.
- Container root filesystem: read-only.
- Network: `none`.
- Temporary execution space: ephemeral writable and executable `/tmp` inside the disposable container.
- Git trust: an external ephemeral runner `HOME` config supplied exact `safe.directory=/workspace`; it did not write host, user, checkout, or repository configuration.
- Test command contract: root Python unittest discovery under `/workspace` against the disposable exact-tree commit.
- Image selection is digest-pinned; no mutable tag is evidence authority.

Equivalent contract shape:

```text
docker run --rm --read-only --network none --user 10001:10001 \
  --mount type=bind,src=<clean-exact-tree>,dst=/workspace,readonly \
  --mount type=bind,src=<clean-exact-tree-gitdir>,dst=/workspace/.git,readonly \
  --tmpfs /tmp:rw,exec,nosuid,nodev \
  --env HOME=<ephemeral-runner-home-with-exact-workspace-trust> \
  --workdir /workspace \
  ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2 \
  python3 -m unittest discover -s tests
```

The placeholders describe disposable local paths and contain no credential or persistent configuration. The immutable image digest, exact commit, identity, read-only mounts/root, isolated network, ephemeral executable temporary space, exact Git trust, working directory, and test command are the recorded execution boundary.

## Evidence boundary

This is local verification evidence for disposable commit `ec341a22874872e50b2e73f05e6934c816f6fcc6`. It is not the GitHub App-owned policy-epoch Check Run on an exact pull-request head SHA, is not a human-signed approval, and does not authorize push, merge, release, deployment, or any external action.

Release review, final fingerprint-bound receipts, package `ready` transition, and the external pull-request exact-SHA merge gates remain pending.

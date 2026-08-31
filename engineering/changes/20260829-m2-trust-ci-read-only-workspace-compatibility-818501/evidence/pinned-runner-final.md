# Final local pinned-runner evidence

## Result

- Disposable exact-tree test commit: `3a973b6a8194e752a9ea8d7137a1d7856f76776d`.
- Test result: **386/386 PASS**.
- Duration: **234.638 seconds**.
- Runner image: `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`.

## Exact execution contract

- Container identity: UID/GID `10001:10001`.
- Working tree mount: `/workspace:ro`.
- Git metadata mount: `/workspace/.git:ro`.
- Network: `none`.
- Test command contract: root Python unittest discovery under `/workspace` against the disposable exact-tree commit.
- Image selection is digest-pinned; no mutable tag is evidence authority.

Equivalent contract shape:

```text
docker run --rm --read-only --network none --user 10001:10001 \
  --mount type=bind,src=<exact-tree>,dst=/workspace,readonly \
  --mount type=bind,src=<exact-tree-gitdir>,dst=/workspace/.git,readonly \
  --workdir /workspace \
  ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2 \
  python3 -m unittest discover -s tests
```

The mount sources above are descriptive placeholders for the disposable exact-tree checkout and its Git directory; the image digest, container identity, destinations, read-only flags, network isolation, working directory, and test command are the recorded execution contract.

## Evidence boundary

This is local verification evidence for the disposable exact-tree test commit. It is not the GitHub App-owned policy-epoch Check Run on an exact pull-request head SHA, is not a human-signed approval, and does not authorize push, merge, release, deployment, or any external action.

Independent re-review2, release review, fingerprint-bound receipts, package `ready` transition, and the external PR exact-SHA merge gate remain pending.

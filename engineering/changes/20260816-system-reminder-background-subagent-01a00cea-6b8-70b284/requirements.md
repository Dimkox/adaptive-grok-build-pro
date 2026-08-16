# Requirements — publish 2.0.10

## Acceptance criteria

- [ ] Given `v2.0.9` already exists, when this ships, then `VERSION` and `__version__` are `2.0.10`.
- [ ] Given the shipped tree, when tests run, then structure/package pins expect 2.0.10.
- [ ] Given pack after the bump, when the zip is opened, then in-zip `VERSION` is 2.0.10.
- [ ] Given last mile, when `gh release list` is read, then Latest is `v2.0.10` and `v2.0.9` still peels to `f72c0fc`.
- [ ] Given rollback, when the Release is deleted, then `v2.0.9` remains Latest. No force-push.

## Failure and edge cases

- Do not retag `v2.0.9`.
- Do not add GitHub Actions or `pyproject.toml`.
- Dirty session change-package markdown is not product.

## Non-functional requirements

- Security: no secrets in zip; no `.env` read.
- Reliability: annotated tag + GitHub Release with sha256 sidecar.
- Observability: CHANGELOG §2.0.10 + README Current state name 2.0.10.

# Requirements — deliver the deterministic v2.0.17 artifact child

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: the tracked ZIP and sidecar exist and match `770f1db5…` / 10 940 676 bytes with the exact `<sha>  <name>` sidecar text.
- [x] AC-002: `local_candidate` reports `artifact_bytes_delivered`, `pending_tag_and_release`, `built_byte_reproducible_twice`, and names the release-sync commit and tree as `source_parent`/`source_parent_tree`.
- [x] AC-003: `published`, `external_effect`, `operational_activation` are false, `published_at`/`checked_head`/`merge_commit`/`tree`/`pull_request` are null, and `artifact_child.commit`/`tree` are null.
- [x] AC-004: no identity literal moved; `tests.test_structure` still passes against the release-sync wording.

## Failure and edge cases

- A build taken from a dirty tree or a later tip would silently ship bytes no commit can reproduce; the two-clone digest check and the recorded `source_parent` are the guard.
- Claiming `published: true` here would predate the tag and is a forbidden outcome, not a bookkeeping preference.
- The local verifier flags the >10 MB tracked binary it never reads (issue #80); that is a known local-only red and is disclosed rather than suppressed, with the App-owned exact-head check as merge authority.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority; nothing here restates a governance digest.

- Applicable rule IDs: release-governance (`R -> A -> tag -> SR`), packaging reproducibility.
- Intentional debt created: none.

## Non-functional requirements

- Security: excludes `.env`, keys and credential stores; no secret read during packaging.
- Reliability: byte-identical dual build.
- Observability: dual-build digest, exact-head App check.

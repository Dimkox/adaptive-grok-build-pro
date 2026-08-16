# Architecture — publish 2.0.10

## Current behavior

HEAD `f72c0fc` is tagged `v2.0.9`. GitHub Latest is `Adaptive Grok Build Pro v2.0.9`. VERSION is 2.0.9. A new «релиз сделай» must not retag that SHA.

## Proposed behavior

New identity 2.0.10 on a new commit: pin tests first, then identity files, then pack, verify, independent reviews, publish.

## Components and boundaries

Same eight pin surfaces as 2.0.9, plus new `engineering/runbooks/publish-v2.0.10.md`. Leave `packages/…v2.0.9.zip*` and `publish-v2.0.9.md` frozen.

## Decisions

- Next SKU is 2.0.10 because `v2.0.9` exists.
- Controller implements; no second write agent.
- Session evidence under other `engineering/changes/*` stays uncommitted.

## Risks and mitigations

- Retag 2.0.9: forbidden; new annotated tag only.
- Pack before VERSION bump: zip name would still be 2.0.9. Pack last.
- Force-push / GHA / pyproject: forbidden.

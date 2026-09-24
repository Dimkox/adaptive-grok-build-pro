# Requirements — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given the checked-in policy example, when a reviewer inspects its marker
  and Trust CI README, then the example is explicitly illustrative-only and
  the server-mounted policy epoch plus exact App-owned Check Run are named as
  authoritative.
- [x] Given the dated L5 observation, when a reviewer inspects its provider
  probe section and structure test, then probes are operator-attested and
  non-re-derivable while durable artifact jobs remain the re-derivable evidence.
- [x] Given issues #35, #36, #39, #48, #73 and #167, when the repository is
  searched for their affected seam, then absent/external seams remain recorded
  as blockers and no fabricated implementation is added.
- [x] Given the final frozen tree, when the exact PR verifier and both selected
  independent reviews run, then all required receipts bind to one fingerprint.

## Failure and edge cases

- A checked-in example must not be read as deployed authority or approval
  evidence.
- A provider probe with usage or HTTP output but no durable job row must not be
  represented as a durable verification result.
- A missing external implementation seam must remain an explicit boundary;
  the task fails closed rather than inventing a consumer, provider, or host
  integration.
- Any tree change after verification or review invalidates its receipt and
  requires a fresh run.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: never elevate repository examples, local receipts, or provider
  observations into merge authority.
- Reliability: preserve current check names and runtime behavior; keep the
  change reversible by reverting the bounded docs/test edits.
- Performance: no new network, database, provider, or build dependency.
- Observability: structure tests and the change package identify the exact
  evidence boundary and external blockers.

## Bounded source-owned result

- [x] The checked-in Trust CI policy example is marked `illustrative-example-only`; deployed policy remains external.
- [x] Runtime documentation distinguishes operator-attested provider probes from durable artifact jobs.
- [x] Issues whose source seam is absent (#39 and #48) remain external findings and are not closed by a fabricated patch.

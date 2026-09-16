# Requirements — release-chain convention and inspected causes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: `START_HERE.md` states that release-chain commits (R, A, SR) are recorded through `current_unreleased_change`/`local_candidate` and not as `post_v2_0_16_landing` rows, with row #81 explained as the previous chain's recorded successor.
- [x] AC-002: the `work_inventory` entries for PRs #33, #15 and #21 each name the failing mandatory command, the summary line (`Ran …`/`FAILED …`) and the verbatim assertion or error text, each attributed to a single head and kept labelled as a historical observation; nothing is claimed beyond what the retained record states.
- [x] AC-003: the commit claims and performs no release action, and every published release record stays byte-unchanged.

## Failure and edge cases

- A cause quoted from a superseded head must be attributed to that head, not to the pull request as a whole, and must be labelled historical so a later agent does not read it as a current gate result.
- If a cause is not recoverable from a retained record, the entry must keep saying so rather than being rewritten with an inference.

## Governance context

Canonical governance JSON stays separately reviewed; nothing here restates a governance digest as authority.

## Non-functional requirements

- Security: quoted text is command and assertion output only; no credential, key or host identity.
- Reliability: coupled test literals move in the same commit.
- Observability: the exact-head App check remains the only merge authority.

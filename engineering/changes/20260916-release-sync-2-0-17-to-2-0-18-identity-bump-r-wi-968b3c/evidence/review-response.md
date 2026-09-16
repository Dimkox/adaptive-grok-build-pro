# Review response — v2.0.18 release sync (R)

Both route reviews returned PASS on `ee2cb85`; dispositions below land in one follow-up commit so the
pull request opens on the corrected tree and the final local gate runs on exactly what is pushed.

## `review-security.md` — PASS (0 Critical, 2 Important, 2 Minor)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Important — FORBID-002's letter ("no machine-local runtime state entering the diff; the dossier carries only allowlisted observation fields") vs the carried convention: MainPID/ActiveState/UnitFileState do enter, and the named allowlist existed nowhere in the repo | **Fixed at the typed level.** FORBID-002 now enumerates the actual allowlist the post-91…post-99 dossier chain always carried (unit names, MainPID, ActiveState/UnitFileState, ExecStart release path, installed SHAs, job ids and digests, timings, PR/check identifiers, observation timestamps). The convention and the contract now agree; no value is newly leaked — 44 of the dossier's leaves are byte-identical carries, and the reviewer confirmed zero credentials/hostnames/env content. |
| 2 | Important — `active_delivery.pull_request: 106` read as a linkage to a pull request this wave did not open | **Ruled and fixed.** The field's precedent semantics (78082a2 held `79`, the v2.0.16 publication PR) are "last PUBLICATION pull request", so the truthful value at this stage is `99`; `106` was set with different reasoning (last merged PR) and both reviewers flagged the ambiguity. Now `99`; this wave's own PR number appears only after it exists, in the A/SR waves. |
| 3 | Minor — stale "only open pull request is #33" line in the edited HANDOFF section | Fixed in the same commit (see release-response 3). |
| 4 | Minor — dossier `method` widened to read `ExecStart` | **Kept.** Every value taken from it is byte-identical to the carried `control_repository`; the extra probe makes the re-pin independently checkable, which is what AC-004 claims. |

## `review-release.md` — PASS (3 Important, 1 Suggestion, 2 Minor)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Important — `PROJECT_STATE.json:537` named PR #100's merge as `cfc4a576c3a3…`, an object that does not exist (true SHA `cfc4a5741210cc7b28431c56c92b9d549540c65d`), and it was the sole SHA pointer to the publication successor | **Fixed.** Corrected from `git log origin/main --grep "(#100)"`. Root cause recorded: the wave text was authored from a truncated display read instead of a 40-hex re-derivation — exactly the class of error the landing-row re-derivation rule exists to prevent. All other 27 added 40-hex ids were independently confirmed to resolve. |
| 2 | Important — `active_delivery.pull_request` should be the publication PR (99) or null, not 106 | **Fixed** (ruling above). |
| 3 | Important — HANDOFF bullet still claiming #33 open | **Fixed** with current facts: zero open PRs, #33/#15/#14 dispositions in `work_inventory.retained_unresolved`, #101–#106 merged, #86 remainder and #104 named. |
| 4 | Suggestion — `current_unreleased_change` re-serialized alphabetically while the precedent uses semantic order, leaving two key orders for the same record shape in one file | **Fixed**: keys rewritten in the #98 semantic order. Measured churn stays local to that object; the historical blocks are untouched (INV-001 held: 68 value changes, none in published_release/prior list/milestones/trust_ci/schedule). |

## Coverage limits stated plainly

- The reviews and this response are on tree bytes; merge authority remains only the App-owned
  `adaptive-trust-ci/verified@06ecf1c875bc` on the exact PR head, and the final `grok_verify --mode pr`
  runs on the corrected commit before the PR opens.
- The dossier timestamp cannot be proven from the tree; the release reviewer re-ran its probes on the host
  and got the same MainPIDs, active/enabled state and ExecStart path.

# Review response — A (v2.0.17 artifact child)

Reviewed object: `5b178d3411306143735f6985a1817646e194ea2a` (both reports bind to it). The tree was
then amended once, to fold in the findings below plus the two review reports; that amendment is the
head this pull request is opened and gated on, and the verification/review receipts are taken against
it. The delivered bytes are unchanged by the amendment: the ZIP is built from the recorded
`source_parent` `78082a290f8b90cade88685351fbb2ba263689b9`, not from this commit.

## Independent reproduction performed by the reviewers

Both reviewers re-derived the archive rather than trusting the record, which is the strongest evidence
in this package:

- **security:** a clean detached clone at `78082a2…` (tree `2283e6a0…`, porcelain empty) built in `0700`
  staging produced `770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616` / 10,940,676 B,
  equal to the tracked file and to its git blob; sidecar is exactly 102 B with two spaces and one LF.
- **release:** re-ran the map's build verbatim (two `--no-hardlinks --no-checkout` clones at the recorded
  parent) → `TWO_BUILD_IDENTICAL`, `MATCHES_TRACKED_BYTES`; and executed the delivered-bytes assertion
  block under four conditions: baseline PASS, `tamper-zip` FAILS, `missing-zip` FAILS (`1 != 2`),
  `tamper-sidecar` FAILS. So the test really guards the bytes instead of merely reading them.
- **release:** also verified that no identity literal moved (`VERSION`, `__version__`, README H1 and
  Identity prefix, CHANGELOG heading, ROADMAP product line, the v2.0.16 `packages/README.md` row all
  `EQUAL` per-revision) → `AC-004`, and that the null/false set of `local_candidate` matches the v2.0.16
  precedent's A commit value-for-value (13 fields).

## Findings and disposition

| # | Source | Severity | Disposition |
| --- | --- | --- | --- |
| F1 | release | Important | **Fixed in A.** `GROK_BUILD_HANDOFF.md` item 2 now names the release-sync merge `78082a2…` instead of the pre-R tip, and its section heading reads `observed 2026-09-16` |
| F2 | release | Important | **Fixed in A.** Both mirrored `next_action` fields (`current_unreleased_change`, `active_delivery`) now say: merge A on its exact-head check, then tag + Release under their own grants, then SR. They are asserted equal by `tests/test_project_state.py`, and the replacement was written once and mirrored |
| F3 | release | Minor | **Fixed in A.** `trust_ci.last_success` advanced to PR #98 head `83738723…`, merge `78082a2…`, check run `104605819798`, attestation `96a98471-437c-4bc7-9bef-e2bdf296f258`, and `record_scope` re-dated. One convention line added: release-chain commits are recorded through `local_candidate`, not as `post_v2_0_16_landing` rows |
| F4 | release | Minor | **Deferred to SR**, as the reviewer directed: `CHANGELOG.md:5` still phrases the archive as future ("reaches a release archive only once the artifact child is built"). The "v2.0.16 remains the only published artifact" half stays true and must survive |
| F5 | release | Minor | **Fixed in A.** `README.md` table caption and `START_HERE.md` snapshot now read 2026-09-16, matching the `78082a2…`/PR #98 citation on the adjacent lines and the day-scoped test pin |
| F6 | release | Minor | **Fixed in A.** The release-sync package's `tasks.md` R-merge checkbox is closed with PR #98, its check run and merge commit |
| F7 | release | Minor (pre-existing) | **Deferred to SR** deliberately: `DARK_FACTORY_ROADMAP.md:98` is a dated inventory already qualified by "displayed checks are historical and require fresh base/head validation", it is byte-identical at base, and rewriting it here would widen A beyond the bytes it delivers. `l5_production_preparation.actual_main_observation` was part of this finding and **was** fixed in A |
| F8 | release | Minor (informational) | Accepted as recorded: this route's required evidence is `verification`, `security_review`, `release_review` only, so the absence of a `code_review` receipt is the route's design, not an omission |
| F9 | release | Minor | Accepted with reason: `artifact_child.requirement` deviates from the map's wording because the map text was written before F3 existed; the delivered wording additionally names the four self-identities that must stay null, which is the point of the field |
| S1-S5 | security | Minor | **Deferred to SR** as the reviewer assigned them (stale day labels beyond those fixed here, `CHANGELOG.md:5` clause, HANDOFF residual SHA, dossier list length 3→1). The reviewer confirmed the CHANGELOG *heading* must stay frozen under `AC-004`, so nothing in this section is touched by A |

## Self-correction recorded during this cycle

While preparing the F3 wording I wrote "The artifact child (#99)" into `record_scope`. **No artifact-child
pull request existed at that moment** (`git ls-remote origin 'refs/heads/feature/v2.0.17*'` returned only
the release-sync branch, and `gh pr list --state open` returned only #33), so the number was invented. It
was removed and replaced with a number-free convention sentence before any commit, and
`tests/test_project_state.py` re-ran green (14 tests) afterwards. This is the same failure class filed as
issue #97 and it is recorded here rather than quietly corrected.

## Gate expectations for this pull request

- The local `grok_verify --mode pr` run is expected to report the known issue #80 red on the tracked
  >10 MB binary the analyzer never reads (`Git blob exceeds analysis limit:
  packages/adaptive-grok-build-pro-v2.0.17.zip`). That is disclosed, not suppressed: the precedent
  artifact child (`2b1517`, 10.24 MB) passed all six mandatory commands including
  `repository-verification` on 2026-09-13, so the limit is a local analysis-path difference.
- Merge authority is only `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS for this exact head.
- `published`, `external_effect` and `operational_activation` remain false after this merge; the tag and
  the GitHub Release bind to this pull request's merged commit under their own exact delegated grants,
  and SR is the only commit allowed to record publication.

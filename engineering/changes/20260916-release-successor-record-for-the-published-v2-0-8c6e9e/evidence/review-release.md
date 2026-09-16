PASS

# Release re-review — v2.0.18 successor record (SR)

- Repository: `/home/pall/grok-projects/adaptive-grok-build-sr18`
- Branch: `feature/v2.0.18-successor-record`, HEAD `7380f4a` "docs(release): close the SR review round" (verified `git log --oneline -1`, worktree clean).
- **This report supersedes the FAIL release review of `28de12c`**, re-run at commit `7380f4a` against `git diff 28de12c..7380f4a` (single fix commit, 13 files) plus live sources.
- Reviewer: `release_reviewer` (route `8c6e9e30b239`), read-only; only this file was written. No git mutations, no credential/key/approval-store reads beyond existence probes of runtime grant/receipt paths named below.

## Per-closure verification (each prior finding vs bytes + live reality)

1. **packages/README.md unflipped (AC-004) — CLOSED.** Line 3 now names `v2.0.18` latest published, `2026-09-16T13:52:24Z`, targeting `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`, ZIP `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`, sidecar `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216`. All cross-checked three ways: `published_release` in PROJECT_STATE.json, live `gh release view v2.0.18 --json assets` (both `digest` fields identical), and the annotated tag peel `31d3171f… → e7d0f72…`. v2.0.17 is kept immutable with its correct ZIP `770f1db5…`/sidecar `54db9f64…` (equals prior[0] and the live v2.0.17 assets). Table line 31 now reads `2.0.18 (published 2026-09-16T13:52:24Z)`. Sweep of every "latest published" surface: README.md:7 and DARK_FACTORY_ROADMAP.md:37/42 already correct; the l5-observation runbook's v2.0.16 line is a dated snapshot (legitimate historical).
2. **R (968b3c) / A (f03c54) tasks.md rows — CLOSED, every ticked fact independently true.** A's three rows: reviews PASS on `497de07` (f03c54 `evidence/review-release.md` and `review-security.md` both begin `PASS`; 2+4+2 + 2+4 = 14 findings, all dispositioned in its `review-response.md`); `grok_verify --mode pr` 16/16 on `07d1141` — verification/security_review/release_review receipts for route `f03c541d184f` exist in the `adaptive-grok-build-a18` worktree referencing `07d1141`; PR #108 head `07d1141e…`, merged as `e7d0f72…` 13:51:26Z on App run `104809218211` (live check-run API: `adaptive-trust-ci/verified@06ecf1c875bc`, SUCCESS, head_sha exactly `07d1141e…`); tag `31d3171f…` and Release 13:52:24Z confirmed live; grant `fef0f24d625f4ea3` present in `agbp-main/.grok-stack/runtime/approvals.json`; SR route/package naming matches. R's rewritten row (plus its pre-existing row): PR #107 merged as `fc8d9e6f…` on App run `104782126773` — live check-run confirms that run bound exactly to `f8c5021c…`, which is #107's head. The "state.json intentionally stays" claim is true: 968b3c state.json status remains `implementing`. SR's own final tasks.md row correctly stays **open** (gate on this review-round head not yet run).
3. **Stale candidate wording — CLOSED.** README.md:11 "this candidate's source" → "this release's source"; GROK_BUILD_HANDOFF.md item 4 "source of the 2.0.18 candidate" → "source of the released 2.0.18". The prescribed pending-grep over tracked `*.md`/`*.json` returns only historical/evidentiary hits (prior-wave reports, this package's brief describing the pre-fix state, mistakes.md quoting the defect) — no remaining false current-state claim about v2.0.18.
4. **Duplicate `requirement` assert + dropped `zip_source_note` — CLOSED.** Diff shows the second identical `assertTrue(local["artifact_child"]["requirement"])` replaced by `assertTrue(local["artifact_child"]["zip_source_note"])`; the field exists and the suite is green.
5. **prior[0] underpinned / dead V2017 constants — CLOSED.** prior[0] now pins **11** identity fields: tag, pull_request 99, checked_head, merge_commit, tree, artifact.sha256, artifact.sidecar_sha256, tag_object, trust_ci.attestation_id, published_at, merged_at. Five previously-dead constants (SIDECAR, TAG_OBJECT, PUBLISHED_AT, MERGED_AT, ATTESTATION_ID) are now live assertions; AC-002's rewritten text enumerates exactly these fields (no overstatement). **Mutation proof:** in a fresh 0700 /tmp clone at `7380f4a`, corrupting `prior_published_releases[0].tag_object` made `tests.test_project_state` **FAIL (failures=1)**; clone discarded.
6. **Release body wrong check lineage — CLOSED (external, verified live).** `gh release view v2.0.18 --json body` now attributes run `104809218211` / attestation `8172a5bc-1377-428a-aaa9-b8da462f9952` to PR #108 head `07d1141e…` and labels `104782126773` as the release-sync PR #107's run — both bindings verified against the Checks API above. In-tree values unchanged and already correct.
7. **Dossier service_observation — CLOSED, byte-verbatim.** The field now equals live `systemctl show -p MainPID -p Id -p ActiveState -p UnitFileState adaptive-l5.service adaptive-l5-grok.service` stdout exactly, including the blank-line separator and trailing newline (MainPIDs 698333 / 3597736, both active+enabled, re-confirmed on this host now). Coupled tests pass against it.
8. **mistakes.md — factual.** New entry's symptom (packages/README lines 3/31 naming v2.0.17 latest / v2.0.18 "tag pending" while 119 stayed green), root cause (mirrored the four tested docs + machine records, not the fifth untested surface; file list reused from memory instead of `git show --name-only` on precedent `cfc4a57`/PR #100) and durable rule all match the verified record.

## Re-verification runs

```bash
git log --oneline -1                       # 7380f4a, branch feature/v2.0.18-successor-record, clean
git diff 28de12c..7380f4a                  # 13 files: README, HANDOFF, packages/README, mistakes.md,
                                           # tests/test_project_state.py, SR package docs/evidence, R+A tasks.md rows
gh pr view 107/108, gh api check-runs 104809218211 / 104782126773, gh api git/tags/31d3171f…,
gh release view v2.0.18 --json body/assets # all lineage/digest/target claims re-derived live
python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package tests.test_change_spec
# Ran 119 tests ... OK
# mutation check in /tmp 0700 clone: corrupt prior[0].tag_object -> FAILED (failures=1)
```

## Scope guard

`git diff 28de12c..7380f4a --name-only` contains no contract (`factory/contracts`), rules
(`architecture/`), product code, `scripts/`, or packaging files. The only test change is the
review-mandated assertion hardening in `tests/test_project_state.py`; the only spec change is
AC-002's wording in this package's own change-spec.yaml, now matching what the test guarantees.
`packages/README.md` is documentation, not packaging behavior.

## New observations (non-blocking)

- Pre-existing at `28de12c` (not introduced or claimed fixed here): `published["gitguardian"]["conclusion"]` is asserted twice (test lines 353/359) — same harmless-duplicate class as finding 4's original defect; a future tidy may dedupe.
- `V2017_SOURCE_BASE` remains referenced only at its definition (comment documents it as the PR #98 base); the five identity constants the finding named are all live now.
- prior[0] does not pin `trust_ci.check_run_id`, `gitguardian.check_run_id`, `signer` or `github_app_id`; AC-002 no longer claims coverage of those, so record and guard agree. Adding them is optional future hardening.

## Verdict

All seven FAIL findings plus the disposition table's items are closed against bytes, and every
newly ticked fact independently re-derives true from GitHub, the tag, the release assets and the
live host. No new defect and no false assertion found in the review round. **PASS.**

## Limits

- The final `grok_verify --mode pr` on a head containing this report and both review files has
  not run yet (SR tasks.md final row, open, correctly); this review created no receipt and made
  no git mutation outside writing this file. Merge authority remains solely the App-owned
  exact-head check on the successor PR head, plus the human gate — local receipts and this PASS
  are preflight evidence only.
- Grant/receipt verification was existence-and-association only (file paths + id strings); grant
  content, approval keys and credential stores were not read.
- Attestation UUIDs were taken from the release body / check-run record fields, not from the
  Trust CI API or its signing material.

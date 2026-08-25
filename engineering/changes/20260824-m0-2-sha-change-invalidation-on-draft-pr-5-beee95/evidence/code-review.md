# Code review — M0.2 SHA-change invalidation (draft PR #5)

Reviewer: `code_reviewer` (read-only). Route `beee95e0b3c6`. Change `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`.

Tree reviewed: commit `ce03c87b3d9b8767105c01270869e33b50af56df` vs parent `ca1e88aad3dafcfeb81583f443f67c49c1faeab6`. Uncommitted `evidence/sha-invalidation.md` and `evidence/implementation.md` read as operator evidence only (intentionally not in the commit).

No push, merge, deploy, PEM/`.env` reads, or GitHub mutation.

## Verdict

**PASS.** The commit is paperwork-only, matches the slice contract, and live GitHub state proves SHA-bound Check Run invalidation without forging success.

## Diff vs contract

- 21 files: this change package (analysis/brief/architecture/route/state) plus leftover `85a17e` `code-review.md` / `test-review.md` / `state.json` (implementing → ready).
- No `trust-ci/**` product code, tests, policy, or compose in the commit.
- Tracked `trust-ci/compose.yaml` identical parent vs `ce03c87` (sha256 `bb399c7569fc01742e5b24d900c9dfab4bb47efedc87ce359e887613d06d2eb6`).
- No `BEGIN … PRIVATE KEY`, PEM blocks, or token-shaped material in the commit (only documentation mentioning those markers as test strings).
- Infinite-SHA ruling held: live ids live in uncommitted `sha-invalidation.md`; they are **not** in `ce03c87`.

Placeholder `change-spec.yaml` (`{{OBJECTIVE_STATEMENT}}`) is workflow scaffolding, not a product defect for this ops slice.

## Independent GitHub facts (2026-08-24)

| Claim | Observed |
| --- | --- |
| PR #5 draft, not merged | `draft: true`, `state: open`, `merged: false` |
| Head SHA | `ce03c87b3d9b8767105c01270869e33b50af56df` |
| Base | `main` @ `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| `main` protection | HTTP 404 `Branch not protected` |
| Old Check Run `97390635614` | still `head_sha=1fc942065a124ce75659bd082519d8ebc37774e8`, App `4694114`, `external_id=1b63d10b-90c1-498a-97b8-7b5e0ea76aec`, conclusion `action_required` |
| New Check Run `97406973020` | `head_sha=ce03c87…`, App `4694114`, name `adaptive-trust-ci/verified@6737355947c2`, `external_id=54e2c6f4-ed18-45dd-abfb-2074fb8ee96a`, conclusion `action_required` |
| Old run on new SHA | **absent** from `ce03c87` check-runs list |
| Forged success | **no** — Trust CI conclusions remain `action_required` |

Matches uncommitted `sha-invalidation.md` / `implementation.md`. `action_required` is publication success, not merge eligibility.

## Findings

1. **Info — product compose untouched.** Host-socket overlay remains untracked by design.
2. **Info — not M0.2 complete.** Policy-epoch pass and human Ed25519 scopes are out of this slice.
3. **Low — template change-spec.** Fill before treating this package as a product change record.

## Recommendation

Accept the SHA-change paperwork commit and live proof. Do not merge. Do not PATCH the old Check Run. Do not commit `sha-invalidation.md` onto the PR head this slice.

**Status: pass.**

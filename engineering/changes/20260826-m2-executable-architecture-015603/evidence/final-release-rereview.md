# M2-A final release re-review — final-review fix wave

## Exact identity

- Route: `0156034c05bd`
- Change: `20260826-m2-executable-architecture-015603`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Prior reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438` (tree `bae34faabdf968396e393d40f7219d3bbf5a60b5`)
- Fix head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` (tree `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`)
- Exact fix range: `99de2f9757400f7394b7a9e2c46b3ebce939e438..fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Exact packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-99de2f9..fd5f7eb.diff`
- Packaged-diff SHA-256: `ac1aba14c8498f1c3d1fd6fbd9de7ef7557b09c8c14c9461ce7d5921a3acca54`

## Verdict

**BLOCKED — the M2-A fix head is not locally source-ready.** Original release findings REL-FINAL-I1 and REL-FINAL-I2 remain open, three new Important source/contract failures were independently reproduced, the package contains contradicted completion claims, and REL-FINAL-I6 is unsatisfied. This verdict is local source/readiness evidence only; no external deployment or Trust CI action is required to reach it.

Current finding count for release disposition: 0 Critical, 6 Important, 0 newly introduced Minor. PASS requires zero Critical and Important findings.

## Original release finding disposition

| Prior finding | Verdict | Exact evidence |
|---|---|---|
| REL-FINAL-I1 — queue wildcard/structured provenance | **NOT ADDRESSED** | `final-test-rereview.md` reproduces three wildcard-derived aliases that still return `background=not_applicable`, `overall=pass`, and no `new_queue`. It also reproduces three mixed-container false positives. The literal direct cases were repaired, but the original fail-closed provenance boundary remains incomplete. |
| REL-FINAL-I2 — installer target containment | **NOT ADDRESSED** | `final-security-rereview.md` confirms the ordinary managed-file alias repair, but `_open_dir(create=True)` can still create directories through an ancestor descriptor after that ancestor is relocated outside the repository. `final-test-rereview.md` additionally reproduces rollback mode loss (`0666` becomes `0644` under umask `022`). |
| REL-FINAL-I3 — adoption forgotten after a later descendant | **ADDRESSED for the original sequence** | `final-code-rereview.md` confirms that actual adoption-marker history remains fail-closed after deletion and a later descendant. A distinct new compatibility regression is recorded below: abandoned pre-marker drafts now falsely count as durable adoption. |
| REL-FINAL-I4 — unknown line statistics treated as zero | **ADDRESSED** | `final-code-rereview.md` and `final-test-rereview.md` confirm NUL/invalid-UTF-8 applicable artifacts produce scoped `unsupported`, overall failure, and monotonic risk rather than a zero-valued pass. |
| REL-FINAL-I5 — `_run_capped` selector setup leak | **ADDRESSED** | `final-code-rereview.md` and `final-test-rereview.md` confirm selector construction, nonblocking setup, and registration failures normalize, close/reap the real child process, and do not leave it live. |
| REL-FINAL-I6 — exact-fingerprint review/receipt gate | **NOT ADDRESSED** | All four available independent scoped rereviews are `BLOCKED`: code (1 Important), test (2 Important), security (1 Important), and data (1 Important). `scripts/grok_status.py` reports all six required receipts missing, including verification and all five review kinds. |

## Important release blockers at the fix head

### REL-RR-I1 — queue provenance still fails both sides of the safety contract

The fix does not propagate wildcard uncertainty through aliases/factories, so real Celery and RQ jobs can still be classified N/A/pass. It also overtaints heterogeneous tuple/list/dict values and reports ordinary local `.task` use as a new queue. These are independently reproduced production-behavior failures, not merely missing tests. Required closure is the bounded per-value provenance repair and adversarial matrix specified in `final-test-rereview.md`.

### REL-RR-I2 — installer mutations and rollback are not relocation-safe

Directory creation can escape through a descriptor whose ancestor has been moved outside the current target tree; the installer neither revalidates the complete current-root path nor rolls back the directories created through the relocated descriptor. Separately, the file rollback staging path relies on the creation mode without `fchmod`, so umask can strip target-owned permissions during a failed relocation repair. This keeps the original installer release blocker open and invalidates a claim that failed installation preserves the target unchanged.

### REL-RR-I3 — durable-adoption repair breaks the documented marker authority and rollback contract

Historical model/rules drafts are treated as proof that explicit adoption occurred even when `architecture/adoption.json` never existed. The end-to-end reproduction in `final-code-rereview.md` changes an abandoned pre-marker draft lifecycle from legacy `not_configured` to failure. That contradicts the marker-last authority described in `QUICKSTART.md` and makes `rollback.md:13` false for a repository that committed and later removed unadopted drafts. Historical marker evidence must be distinguished from historical draft evidence while retaining fail-closed handling for real marker deletion and shallow ambiguity.

### REL-RR-I4 — the frozen M2-B source contract publishes stale canonical digests

`engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:21-22` publishes composite/system digests `ca97384d...` / `f8eeaf18...`. The exact fix head reports `ea8750fcec55d8880d142981764e6842e944424cf5c5b4bf89d13b3713f85c8a` / `feb9f1596d664a5909dfb7e0d76ec379ca8ddb77e616b970aeef6ba32c5c869c`. This makes the claimed frozen handoff contract for AC-007 unusable even though the current schema, rules, and inventory digests remain consistent. The literals need correction plus a bounded equality check against the canonical summary.

### REL-RR-I5 — package progress claims contradict the independent results

`engineering/changes/20260826-m2-executable-architecture-015603/tasks.md:12`, `.superpowers/sdd/2026-08-26-m2a-executable-architecture/progress.md:74`, and the appended final-review fix-wave report claim all seven Important source findings were repaired. The actual test and security rereviews explicitly classify the queue and installer findings as **NOT ADDRESSED**, and the data/code rereviews find additional Important breakage. The high-level `README.md`, roadmap, `release.md`, and `state.json` correctly remain candidate/implementing/pending; the contradicted package completion claims must be corrected before release evidence is truthful.

### REL-RR-I6 — local evidence gate is red and receipts are absent

The exact-head code, test, security, and data rereviews are all `BLOCKED`; this release rereview is also `BLOCKED`. In addition, `scripts/grok_status.py` lists missing `verification`, `code_review`, `test_review`, `security_review`, `data_review`, and `release_review` receipts. No receipt should be recorded as passing until the Important findings are repaired on a new immutable head and the complete route-selected wave passes there.

## Documentation, rollout, rollback, and boundary audit

- `README.md:11`, `DARK_FACTORY_ROADMAP.md:416-451`, `release.md`, `tasks.md:13-14`, and `state.json` do not claim PR, merge, M2-B, deployed enforcement, or production completion. `state.json` remains truthfully `implementing`.
- README version identity remains consistent, and `python3 -m unittest -v tests.test_structure` passes all 12 checks, including the exact 120-edge decorative-only K16 invariant, version identity, no GitHub Actions, and external merge-trust wording.
- `final-review-brief.md` now binds the exact fix head and preserves the source-only/external-boundary disclaimer.
- `rollback.md` remains non-destructive and correctly states that no database, migration, service, queue, external write, or deployed Trust CI rollback is part of M2-A. Its unadopted-draft `not_configured` statement is nevertheless unsafe until REL-RR-I3 is fixed.
- `git diff --check` passes for the exact fix range. That range changes no path under `trust-ci/**` or `.github/workflows/**` and adds no authorized external operation.

## Pending gates and disclaimer

Local source readiness is blocked by repository defects and evidence truth, not by missing authority to push, deploy, or mutate Trust CI. After source repair, a new commit must receive fresh exact-fingerprint verification, all five independent route reviews, and matching local receipts. PR delivery, the GitHub App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` check on the exact PR head, signed external approvals, merge, M2-B activation, and deployment remain separate operator-controlled gates.

This review made no product-code, package-state, runtime-receipt, Trust CI, credential, branch, PR, deployment, service, database, or external-system mutation. Concurrent reviewer reports are local workflow evidence and are not part of the reviewed Git tree or merge authority.

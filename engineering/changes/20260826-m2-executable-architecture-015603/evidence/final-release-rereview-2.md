# M2-A final release re-review 2 — second consolidated fix wave

## Exact identity

- Route: `0156034c05bd`
- Change: `20260826-m2-executable-architecture-015603`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Prior reviewed head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` (tree `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`)
- Fix head: `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad` (tree `f142f13d7407d0bf62439acb3f12a4339b21b51a`)
- Exact fix range: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d..52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`
- Exact packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-fd5f7eb..52c4ab8.diff`
- Packaged-diff SHA-256: `f6645ae122d1fd000796ace4eb2306e57a9b3a60f5461de6524492c6a34f750b`

## Verdict

**BLOCKED — the second M2-A fix head is not locally source-ready.** The adoption-history, frozen-digest, and package-truth blockers are addressed, and the literal installer directory/mode repairs work, but queue analysis still fails open for reachable queue values, exact non-queue selections can fail incorrectly, and installer recovery can leave mutated bytes plus staging residue. The final-review brief is stale and the exact-head evidence gate is red.

Release finding count: 0 Critical, 5 Important, 0 Minor. PASS requires zero Critical and Important findings.

## Prior release-blocker disposition

| Prior blocker | Verdict | Evidence |
|---|---|---|
| REL-RR-I1 — queue provenance | **NOT ADDRESSED** | The prior wildcard-alias and mixed-container examples are repaired. However, `final-code-rereview-2.md` reproduces traversal-order and Python-equal-key false negatives, while `final-test-rereview-2.md` reproduces queue loss through container mutation/concatenation and false positives for exact negative indexes/keys. The replacement resolver still violates both directions of the applicability contract. |
| REL-RR-I2 — installer relocation and rollback safety | **NOT ADDRESSED overall** | Directory creation relocation and successful rollback byte/mode restoration are addressed. However, `final-code-rereview-2.md` and `final-security-rereview-2.md` independently identify the same rollback-publication failure: the replacement remains published, the original is not restored, and the second stage is untracked and left behind. This is still inside the original failed-install recovery boundary. |
| REL-RR-I3 — abandoned drafts falsely establish adoption | **ADDRESSED** | History inference now queries only canonical `architecture/adoption.json`; the new four-commit marker-free draft regression returns legacy `pass/not_configured`, while actual marker deletion, merge, shallow, current, and route-base partial-authority cases remain fail-closed. |
| REL-RR-I4 — stale frozen M2-B digests | **ADDRESSED** | `requirements.md:17-25` publishes the current composite/system values, and `tests/test_structure.py` binds all five frozen literals to `grok_architecture summary --json`. The exact-head data rereview is PASS. |
| REL-RR-I5 — contradicted package completion claims | **ADDRESSED for the prior claims** | `tasks.md`, `release.md`, state, and progress now describe a second source candidate requiring independent review and receipts rather than claiming all prior blockers closed. A distinct stale exact-head review brief is recorded below. |
| REL-RR-I6 — exact-head reviews and receipts | **NOT ADDRESSED** | Exact-head code, test, and security rereviews are BLOCKED; data rereview is PASS. `scripts/grok_status.py` reports all six required receipts missing. |

## Current Important blockers

### REL-RR2-I1 — queue provenance depends on assignment order and models equal Python keys inconsistently

The fixed-point resolver keeps one value per name and overwrites it for alternative definitions rather than joining reachable possibilities. A Celery receiver assigned in one branch and a local receiver in the other can therefore be classified N/A/pass solely because the local branch is visited last; reversing branch order changes the result. The keyed representation also distinguishes boolean and integer keys that Python treats as equal, allowing a queue value selected at runtime to be analyzed as non-queue. Both independently reproduced cases violate AC-004/FORBID-002 and the fail-closed applicability contract. The repair must conservatively join alternative definitions and implement exact supported key equivalence or fail closed on collisions.

### REL-RR2-I2 — container mutations disappear while exact signed selections overtaint non-queue code

`final-test-rereview-2.md` independently reproduces three real Celery task false negatives after `append`, subscript assignment, and list concatenation: every case returns N/A/pass/no trigger. The same bounded model treats statically exact negative list indexes and negative integer dictionary keys as unresolved mixed selection, inventing `unsupported` and `new_queue` for a local non-queue value. A bounded structured-operation policy must either resolve or conservatively taint relevant mutation/combination, while normalizing signed integer keys and Python negative indexing for exact selections.

### REL-RR2-I3 — rollback publication failure leaves an external partial mutation and unmanaged stage

After first publication and relocation detection, the recovery stage is held only in local `rollback`, while the outer cleanup owner `stage` has already been cleared (`scripts/install_into.py:335-378`). If the rollback `os.replace` fails, replacement bytes/mode remain in the relocated parent and `.adaptive-install-*` residue remains under the target. The committed regressions cover initial-stage failure and successful recovery, not failure to allocate/publish the rollback stage. Every stage needs one cleanup owner before any publication, and failure injection must prove exact bytes/mode and zero stage/parent residue—or publication must be redesigned so restoration cannot become best-effort.

### REL-RR2-I4 — the final route-review brief names the prior head as current

`.superpowers/sdd/2026-08-26-m2a-executable-architecture/final-review-brief.md` still declares reviewed head `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` and exact range `25bfbe59...fd5f7eb`, while the candidate is `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`. This is a load-bearing exact-SHA review instruction and contradicts the appended second-wave report. It must bind the actual final immutable head; that documentation write will itself require fresh exact-head evidence.

### REL-RR2-I5 — required exact-head evidence is red and receipts are absent

At the reviewed state, code rereview is BLOCKED with two Important findings, test rereview is BLOCKED with one Important finding, security rereview is BLOCKED with one overlapping installer finding, and data rereview is PASS. Verification/code/test/security/data/release receipts are all missing. Consequently AC-007 and the package go/no-go criterion requiring five passing independent reviews on one fingerprint are not satisfied.

## Release, rollback, status, and boundary audit

- `state.json` remains `implementing`; `requirements.md` leaves AC-007 open; `tasks.md` leaves residual closure, all five reviews/receipts, and M2-B unchecked. `release.md` explicitly says the second candidate requires fresh review and makes no ready/deploy claim.
- `README.md` and `DARK_FACTORY_ROADMAP.md` continue to call M2-A a local source candidate and keep final reviews, receipts, PR delivery, external Trust CI, M2-B, and deployment pending.
- The source-only rollback remains non-destructive and its marker-free `not_configured` statement is consistent again after the adoption-history repair. No database, migration, service, queue runtime, or external-state recovery applies. Installer failure recovery is nevertheless not trustworthy until REL-RR2-I3 closes.
- `python3 -m unittest -v tests.test_structure` passes all 13 tests, including exact 120-edge decorative-only K16 completeness, current frozen digests, version identity, external merge-trust wording, and absence of GitHub Actions.
- `git diff --check` passes for the exact second-wave range. That range changes no path under `trust-ci/**` or `.github/workflows/**` and performs no push, PR, merge, deployment, approval, credential, database, service, or external mutation.

## Pending gates and disclaimer

This BLOCKED decision is based on local source defects and current evidence truth, not on absent permission for external operations. After repair on a new immutable head, rerun exact-fingerprint verification and all five independent reviews, record only matching passing receipts, and update the exact-head review brief. PR delivery and the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact PR head, signed external approvals, merge, M2-B rollout, and deployment remain separate operator-controlled gates.

This review modified only this report. It did not modify product code, package state, receipts, Trust CI, credentials, branches, services, databases, or external systems. Local reports and passing tests are workflow evidence only, never merge authority.

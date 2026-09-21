# Independent code review

**Result: FAIL — one blocking routing regression.** One additional documentation finding is nonblocking. This report is local review evidence, not merge authority.

- Reviewer: selected `code_reviewer`, independent of implementation.
- Route: `bcc1d645c438`.
- Reviewed base: `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
- Reviewed head: `4a8e8925478e390d7bf12f2bf4faab8fc0e0c70c`.
- Worktree: `/home/pall/grok-projects/adaptive-grok-build-reviewed-batch`.
- Scope: the actual base-to-head diff, `brief.md`, `change-spec.yaml`, `candidates.json`, all 19 imported product/test paths, and relevant callers. Source review performed on September 21, 2026.

## Findings

### C1 — P1 / blocking: preserve authentication and authorization security routing

Location: `.grok-stack/adaptive_grok/router.py:230` (new matching branch), with the security keyword table at line 37 and risk selection at lines 264–275.

The new `re.fullmatch(r'\w{1,4}', term)` branch treats `auth` as a standalone word. `_has_term` then rejects both `authentication` and `authorization` because a word character follows `auth`. Neither full form has another entry in `DOMAIN_KEYWORDS['security']`. The old domain scorer matched the `auth` stem in both words. `HIGH_RISK` does not compensate: it also contains only `auth` for these cases and has already used the same whole-word helper.

For a generic repository and the concrete prompt `Fix authentication`, the code therefore changes the route from security / high risk / high-risk complexity to generic / low risk / micro. The resulting route loses `security_reviewer`, `release_reviewer`, `security-sensitive-change`, and `scope_and_design_approval` (review selection at lines 373–382, skill selection at lines 397–409, gate selection at lines 436–440). `Fix authorization` has the same regression. A repository background domain such as API can still retain contract checks, but does not restore the lost security classification.

This is a local workflow and review-gate regression; it does not by itself replace or bypass external Trust CI authority. It nevertheless contradicts preservation of meaningful specialist routing for genuine security work. Existing added router tests exercise false-positive substrings and several standalone technical keywords, but do not cover these common authentication/authorization prompts.

Repair through the selected write owner: retain the intended boundary for short standalone tokens while explicitly preserving genuine authentication/authorization terms, then add regression coverage for both prompts and their resulting risk, security reviewer, skill and human gate. The security reviewer raised this concern during the review; I independently confirmed the old/new behavior by tracing the actual source. No execution was performed for this finding.

### C2 — P3 / nonblocking: refresh the README verification state during the final handoff

Location: `README.md:16`.

The paragraph still states that combined verification is pending. The preserved result and `START_HERE.md` / `PROJECT_STATE.json` record its PASS at `4bbbad340fee79e2d2e9d2598a6f58daa6c5b541`. Update this sentence when recording the next verified/reviewed state, keeping that historical run distinct from final-head receipts and external checks.

## Scope and interaction checks performed

I used read-only Git inspection, source/test/document reading, and standard-library JSON/hash inspection. I did not run tests, lint, compilation, Docker, product imports, database commands or behavioral probes. I did not modify source, the index, HEAD or receipts; this report is my only write.

- Compared Git tree entries for every manifest product/test path between its exact candidate commit and the reviewed head. All 19 blobs and modes match: router 4, receipt schema 2, consumer docs 4, fingerprint 4, schema references 4, migration-prefix tests 1. Candidate identity does not resolve finding C1.
- Inspected all 283 changed-path names. Apart from those 19 paths, changes are confined to `engineering/changes/` and the declared shared handoffs (`PROJECT_STATE.json`, `README.md`, `START_HERE.md`, `decisions.md`, `mistakes.md`). No net SQL resource, factory production source, Trust CI source, GitHub Actions, or architecture policy/model change appears in this diff.
- Reviewed bounded optional route metadata and its closed-shape loader; receipt-kind schema parity with both runtime registries; and propagation through existing route persistence and change-package copying.
- Reviewed installer inventory/rendering and descriptor-bound source reads. Both consumer documents use inventoried template bytes; factory README mode is retained; the existing absent-target writer and read-only existing-target plan remain unchanged. Added tests cover manifest identity, installed links, consumer ownership, reusable templates and source-race refusal.
- Reviewed fingerprint inventory provenance and receipt/verifier callers. Tracked diff entries remain included even under noise paths, staged deletion/recreation is retained, scratch exclusions require successful tracking inventories, and Git NUL-delimited filesystem bytes remain distinct through fingerprinting and JSON serialization. The new tests cover raw names, literal backslashes, symlink-target bytes, failed inventories, tracked noise and receipt staleness.
- Reviewed schema resolution and dependency closure together. Valid concrete paths take precedence; declared-ID fallback remains available, including the explicitly handled unsafe-path aliases; closure still unions candidate identities. Diagnostic deduplication/capping occurs after traversal and refusal checks, with exact hidden counts per in-scope referrer. Added tests retain late fatal ambiguities, inherited signals and unaffected out-of-scope behavior.
- Reviewed the populated-prefix fixture, real packaged SQL application, migrator transaction/timeout path and worker cleanup. The tests seed actual 001–020 resources, check preserved ledger timestamps/data/function identity/ACL, exercise 021 behavior and idempotent replay, corrupt and restore a real ledger row, observe actual advisory-lock contention, and test release plus timeout/retry. No migration implementation is changed.

## Existing execution evidence and limits

I inspected `combined-full-report.json`, `combined-full-meta.json`, `combined-full-result.json`, and the preserved initial failed result. The successful report records `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, at `4bbbad340fee79e2d2e9d2598a6f58daa6c5b541`, with fingerprint `cf3e65364833e9a5c3efba1e3ebb7f788e9921c493b66aa083dc64b5eb91a5ae`. All required recorded checks pass; workflow artifacts are explicitly unconfigured. The summary records 828 root tests and 782 PostgreSQL/factory tests with two conditional skips. These are inspected prior-run results, not executions by this reviewer.

I independently recomputed the full report SHA-256 as `2e1141e2280d24d2ea373fb8c6565c0a22e1529c6efdc27bf6ae437ac1dc6e9c`, matching the recorded digest. The seven paths changed from that verified commit to the reviewed head are handoff/state documents and the three combined-result artifacts; no product/test bytes changed. The source finding above demonstrates a missing case despite that passing suite.

Declined judgments:

- Fresh runtime correctness, timing repeatability, and platform-specific filesystem behavior: execution was explicitly excluded from this review to preserve the shared verification lane. Static test inspection and prior evidence do not establish a new run.
- Final-head verification receipts, complete route evidence, or PR merge eligibility: the observed run predates the reviewed head, review artifacts change the repository, and this report is FAIL. The corrected tree needs the coordinator's required verification and independent reviews.
- The separate #162 trusted-validator successor: it is explicitly excluded and no Trust CI source was changed; local enum parity proves no external validator upgrade.
- Live Trust CI policy/holdout, human approval scopes, branch protection, ingress availability, deployment and production data: none was contacted or mutated, and repository evidence cannot certify those boundaries.
- Future migration suffixes: the added current-prefix tests adapt to the packaged last migration, but this review assesses only the present 001–021 tree.

Return C1 to the single implementation owner before recording a passing code-review receipt or declaring combined local completion.

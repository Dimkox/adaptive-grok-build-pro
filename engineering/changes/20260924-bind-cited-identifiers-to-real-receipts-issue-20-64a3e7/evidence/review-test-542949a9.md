# Test review — does `tests/test_citation_identifiers` lock issue #206?

## Verdict

**FAIL.** The module contains the incident-shaped cases and 37 of its 38 tests passed on this HEAD, but it does not lock issue #206. Required echo and corpus behaviors have no assertion that would go red, and the review CLI test accepts any 64-hex pass line. Mutation kills were not executed.

reviewed-tree-modified: no

## Identity

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-cite206`
- Branch: `fix/issue-206-receipt-identifier-citation`
- HEAD: `542949a98569a73af533b7c514f6cfcbfd8ec97a` (`git rev-parse HEAD`)
- Subject: `fix: make cited evidence identifiers pasteable and checkable (#206)`
- Porcelain before and after the unit run, and before this report: only the pre-existing untracked `engineering/changes/20260924-bind-cited-identifiers-to-real-receipts-issue-20-64a3e7/evidence/next-gap.md`
- Tree fingerprint: unavailable. The read-only fingerprint command was denied by the shell circuit breaker (ambiguous-sensitive-shell, then the rewrite was denied). It was not retried.
- Scratch: not created. The private mutation-probe command was denied by that same circuit breaker before it ran, so scratch mode, snapshot fidelity, and killed/survived results were not established. No product file was edited.

Issue #206 (open) asks for three things: one canonical `RECEIPT` line from `grok_verify` / `grok_review` carrying kind, fingerprint, `at`, and path; a mechanical existence check that flags a plausible hex, including a real prefix with an invented tail; and guidance to paste that line or write "see receipt file". The change spec adds invocation binding, leaf-only structured authority, and a non-zero citation CLI. This review uses that adopted contract plus the issue text. The deferred choice not to call the checker from inside `grok_verify` / `grok_review` is recorded in `requirements.md` and is not charged as a missing test.

## Executed claim

Claim: the module's tests, except the one that launches `scripts/grok_verify.py`, pass on this HEAD.

Command (worktree, bytecode redirected, verifier not invoked):

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/pyc-cite206 python3 -m unittest \
  tests.test_citation_identifiers.IdentifierExtractionTests \
  tests.test_citation_identifiers.CorpusCorruptsItsOwnTrustTests \
  tests.test_citation_identifiers.GitObjectResolutionTests \
  tests.test_citation_identifiers.ReceiptEchoTests \
  tests.test_citation_identifiers.EchoCliWiringTests.test_grok_review_echoes_a_pasteable_line_for_its_own_receipt \
  tests.test_citation_identifiers.CitationsCliTests -q
```

Observed: `Ran 37 tests in 10.958s` / `OK`, exit 0. A later `git status --porcelain=v1` still showed only `next-gap.md`.

The module defines 38 tests. `EchoCliWiringTests.test_grok_verify_echoes_a_pasteable_line_for_its_own_receipt` was not run, because this review was told not to run `grok_verify.py`.

## What the assertions actually pin

These behaviors are named by an assertion and are green in the 37-test run. They were **not** mutation-probed, so none is scored killed:

- Incident shape: a 64-character id's prefix plus an invented tail is unresolved (`test_real_prefix_with_an_invented_tail_is_unresolved`), and a short id that stands alone in the corpus plus an invented tail is unresolved (`test_a_short_identifier_plus_an_invented_tail_is_unresolved`).
- A faithful prefix and the full id resolve. An unknown Git id does not. Skipping Git only makes the check fail. A real commit prefix resolves.
- Repeating a token in report prose does not authorize it. JSON `title` / `notes` do not; a `spec_fingerprint` leaf does. Nested `description` / `example` under `id`, `version`, or `policy` does not.
- Generated `architecture/generated` text is in the corpus. Symlinked and oversized corpus entries are not. A skipped candidate consumes the file budget.
- Echo: one line, `status=pass`, `fingerprint=`, `path=`, `route=`; no route, wrong receipt id, invalidated receipt, and tree mismatch are `status=unavailable` without `fingerprint=`. A hostile route writes nothing. Envelope fixtures must not leak the fixture id. A pasted echo fingerprint resolves and a padded one does not.
- Citation CLI: missing token exits 1 and prints `MISSING`; two same-named documents stay distinct; a missing path or directory exits 2 with `NOT READ` and no `CITATION PASS`; a symlinked document is not read; oversized file and stdin hit the ceiling; `--warn-only` stays exit 0; declined runs are counted.
- `grok_review` happy path prints `kind=code_review status=pass` and some 64-hex fingerprint, and does not say `invocation-unbound`.

## Why that is not a lock

1. **The canonical line's `at=` field is unasserted.** Issue #206 and both verification-evidence skill copies require `at=<UTC>`. No test in this module contains that field. `test_echo_is_one_line_carrying_the_bound_fingerprint` checks kind, status, fingerprint, path, and route only. `LINE_KEY` is applied to the corrupt-JSON refusal, not to the success line. Deleting `at=` from `receipt_echo`'s success return cannot fail this module.

2. **An absent receipt is unasserted.** `requirements.md` and AC-002 require a route with no receipt file to echo `status=unavailable` and `reason=receipt-not-recorded`, with no identifier. That reason string does not occur in the module. Every echo test either has no route, or writes/plants a file first. Replacing the `if not data` branch in `receipt_echo` with a `status=pass` line that carries a fingerprint cannot fail this module. That is the false-evidence class the issue is about.

3. **YAML prose is unasserted.** AC-004 limits structured authority to typed leaves and identifier maps, and `requirements.md` calls out `statement:` / `reason:` lines in `change-spec.yaml`. Every corpus fixture in this module is JSON, an mmd view, or a symlink/size decoy. `_line_keyed_identifiers` is not driven by any test. Scanning every hex run in YAML would authorize a fabricated id written into a change-spec statement, and this module would stay green. The JSON half of the same rule is asserted.

4. **The review CLI test does not bind the pasted fingerprint to the receipt.** `test_grok_review_echoes_a_pasteable_line_for_its_own_receipt` checks return code 0, the substring `kind=code_review status=pass `, absence of `reason=invocation-unbound`, and a 64-hex `fingerprint=` field. It never reads `code_review.json`. A canned pass line with any 64 hex digits satisfies every assertion in that test. The verify CLI test does compare `fingerprint=` and `status=` to the stored receipt, but that test was not executed here, and it does not cover `grok_review`.

Secondary holes, same conclusion, not separately decisive:

- `reason=receipt-envelope-invalid` and `reason=not-recorded-this-run` do not occur in the module. Envelope tests check "unavailable and no fixture id leaked", not the reason slug. The receipt-id mismatch path is asserted; the timestamp path is not.
- No test passes `--json` or `--no-record`. AC-001's stderr/stdout split and the requirement that `--no-record` print no echo are unlocked. The human-mode verify wiring that would check a stored fingerprint was not run.
- No test reads `AGENTS.md`, `README.md`, `.grok/skills/verification-evidence/SKILL.md`, or `.agents/skills/verification-evidence/SKILL.md`. Those files do currently say to paste the `RECEIPT` line or write "see receipt file", and that existence is not proof. The module will not notice if that guidance is deleted. AC-006 assigns that check to review evidence rather than to this module; this review observed the text, and it is still not a regression lock.
- FIFO cited-document input and automatic invocation of the checker before receipt recording are untested. The latter is an accepted scope cut in `requirements.md`.

## Mutants

| Probe | Result |
| --- | --- |
| Re-add `extended-citation` (token longer than a corpus id it starts with) | inconclusive — scratch command denied before execution |
| YAML full-text scan instead of leaf keys | inconclusive — same |
| Ancestor key authorizes nested prose | inconclusive — same |
| Exact match only (drop faithful prefix) | inconclusive — same |
| Treat over-long runs as identifiers | inconclusive — same |
| Treat Git `missing` as resolved | inconclusive — same |
| Citation CLI exits 0 on `MISSING` | inconclusive — same |
| Drop `at=` from the success echo | inconclusive as a process; statically unreachable by any assertion (finding 1) |
| Absent receipt echoes `status=pass` | inconclusive as a process; statically unreachable (finding 2) |
| Drop the timestamp guard | inconclusive — same blocker; no assertion names `not-recorded-this-run` |
| Drop the receipt-id mismatch guard | inconclusive — same blocker; assertions for `not-recorded-this-invocation` exist but were not mutation-run |
| Rename envelope reason | inconclusive — same blocker; reason slug is unasserted |
| `grok_review` omits `expected_receipt_id` | inconclusive — same blocker |
| `grok_review` prints a canned fingerprint | inconclusive as a process; the review test's assertions accept it (finding 4) |

## Unexecuted claims

- All mutation probes and the candidate tree fingerprint, because the shell circuit breaker denied the probe and forbade a retry. Scratch safety was therefore not established.
- `test_grok_verify_echoes_a_pasteable_line_for_its_own_receipt`, because `grok_verify.py` was out of scope for this review. Static reading shows it checks the stored status and fingerprint for `--mode fast` only.
- `--json` stream selection, `--no-record` silence, FIFO input, and checker auto-invocation, because no test implements them. Auto-invocation is a documented non-goal of this change.
- AC-006 regression locking, because this module never opens the guidance files. Presence was read in this review and is not a test.

VERDICT: FAIL

# GitGuardian incident 37586506 — disposition

**Verdict: (b) historical-only occurrence, a false positive needing operator disposition. Not a still-present literal.**

Evidence, read from the check-run output on head `9f1a2dac` (`gh api …/commits/9f1a2dac…/check-runs`)
and the bot comment on PR #208, both quoted rather than summarised:

- The table row names exactly one occurrence: GitGuardian id `37586506`, `Triggered`,
  `Generic High Entropy Secret`, commit **`b2dc99a4594d929dea9b21ec8de62bc25fb29022`**, file
  `tests/test_citation_identifiers.py`, anchor `…#diff-…R111`.
- The check summary says the scan covered the branch range, not the head alone: “1 secret were
  uncovered from the scan of **2 commits** in your pull request.” That is why the check stays red
  after the head moved from `b2dc99a4` to `9f1a2dac`.
- `git show b2dc99a4:tests/test_citation_identifiers.py` line 111 is
  `self.assertEqual(result['unresolved'][0]['token'], 'aa11bb22cc33dd44')`.
- `grep -rn aa11bb22cc33dd44` over this working tree returns nothing, and line 111 of the same
  file at `9f1a2dac` is an unrelated statement. The flagged string exists in no file of either
  the reviewed head or the fixed tree.

What was nevertheless removed in this contour, so that no future scan of the range has a fresh
fixture to fire on: the raw 20-hex fixture literal `deadbeef…` in
`test_an_unknown_object_id_is_not_resolved_by_git` is now the computed
`UNKNOWN_GIT_ID = _synthetic_hex(0xBADC0DE, 20)`. Every identifier fixture in
`tests/test_citation_identifiers.py` is produced by `_synthetic_hex()`; the only 16-character hex
string left in that file is `digits = '0123456789abcdef'`, the alphabet table the generator indexes
into, which is not an identifier and is not high entropy.

Audit of the whole diff against `origin/main` for added lines containing `[0-9a-fA-F]{16,}` leaves
exactly two kinds of line, both legitimate and neither a fabrication:

1. the alphabet table above;
2. stack-generated change-package state under identifier-bearing keys — `head`, `base_commit`,
   `base_fingerprint`, `human_gates_digest` in this package's `state.json`/`route.json`. Those are
   the real values the citation corpus reads; deleting them would break receipt binding and the
   package gate, and GitGuardian did not flag them.

Action for the operator: dispose incident `37586506` as a false positive (test fixture in a
superseded commit of the scanned range). Revocation/rotation does not apply — the string is a
synthetic test token, not a credential, and it no longer exists in the tree.

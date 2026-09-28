# Independent review FAIL disposition — 2026-09-26

The first restacked candidate was `fa4061bc8d5c1405f5c48436f101ef54efc0e2f2`,
tree `4a7cb659ea400c0347e75eed5af7a967720f3a4c`, repository fingerprint
`9bab3f9d7330aa17d38a6ce8ffafe78ef5fdaa0ae9cc6301d28fb23c3d1ded3c`.
Both route-selected reviews returned FAIL without mutating that candidate:

- code review report SHA-256
  `25ba8d6af78543ada6c4c47a36bbffe9f089ec2a3be192cd964d976490705893`;
- test review report SHA-256
  `3d726ae9a760001953f34ce744a469694e5369b1ce64e2f191effc517c0f3ab1`.

The repair accepts the shared findings: textual selector tokens were not a
liveness proof; a member could be assembled across evidence entries; plural
upper-bound language and exact short-code sets escaped; sentence-global cues
caused false positives; and AC-005 lacked a committed baseline/current
comparison. The successor uses static AST selector/helper/literal binding plus
ordinary executed absent→present→restored probes, atomic evidence entries,
sentence-local cues and a committed exact-route-base error-list census.

The code review stated that current exact-fingerprint verification evidence was
absent. The test review rechecked the runtime receipt and established that this
specific statement was mistaken: `verification.json` was a current PASS for
`fa4061bc…`, route base `5713b407…`, and fingerprint `9bab3f9d…`. That receipt
became stale as soon as this repair changed the repository and is not reused.

Issue #202 proposal items 2 and 3 remain explicitly outside this contour. This
proposal-1 pull request must not be described as closing the complete issue.

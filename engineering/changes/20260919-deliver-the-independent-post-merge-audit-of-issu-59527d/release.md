# Release plan — durable delivery of the #104 post-merge audit

## Deployment

Documentation-only change to `main` through this pull request. No artifact is built, no package bytes change, no
service is installed or restarted, and the product version and release identity are untouched. Landing rows for this
change belong to the next release-sync wave, not here.

Sequence: commit → push branch `docs/issue-104-composition-audit` → open pull request → App-owned
`adaptive-trust-ci/verified@<policy-sha12>` on the exact head SHA → merge only as a separately delegated action.

## Feature flags / staged rollout

Not applicable — no runtime surface, no flag, no default changes.

## Metrics and alerts

No production signal. The observable success check is repository-local and deterministic (`SIG-001`): `mistakes.md`
diff shows additions with zero deletions, and this package's `evidence/` holds one file per completed analysis lane.

## Go/no-go criteria

Go requires all of:

1. `python3 scripts/grok_spec.py validate --gate` → `ok: true`;
2. `git diff --numstat -- mistakes.md` shows 0 deleted lines;
3. the scrub grep for machine-local paths returns nothing;
4. `python3 scripts/grok_verify.py --mode pr` green on the clean delivered head, with `verification` and
   `code_review` receipts bound to that fingerprint;
5. the App-owned exact-SHA check SUCCESS for that same head.

No-go / stop conditions:

- any deleted or reordered line in a shared append-only document;
- any claim in the evidence that cannot be re-run at the SHA it cites;
- any file outside `engineering/changes/<this package>/` and `mistakes.md`.

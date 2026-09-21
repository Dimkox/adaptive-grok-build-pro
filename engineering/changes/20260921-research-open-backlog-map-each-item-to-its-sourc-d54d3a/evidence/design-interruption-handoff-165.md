# #165 — interruption-visible local handoff

Research route `d54d3afd1c92`; execution packet, not implementation or verification evidence. The active delivery controller must select one write owner on a separate routed branch; do not mutate this research route. Requirements below preserve exact-SHA Trust CI and all existing external approval boundaries.

## Outcome and design

An incoming agent can use one cheap status command to identify an incomplete package, last known branch/work state and missing mandatory evidence without launching full verification. Current #155 work is already recovered in PR170; this corrects tooling, not that historical implementation.

Use a pure package inspector and an additive `grok_status` field. Treat uncertainty as a diagnostic, not proof of a crash. Required signals: unknown objective target/success metric; empty acceptance criteria at a stage that requires them; known unexpanded template markers; mandatory evidence lacking either a real run entry or explicit `not_run` plus reason; and dirty product state with zero commits ahead of the known base. A valid newly-created draft is incomplete by design and must be labelled draft rather than corrupt.

## Bounded sequence and acceptance

1. Create `package_completeness(root, package, git_snapshot)` as a bounded, nonmutating inspector, in a focused module if needed. Test complete package, legitimate fresh draft, missing file, malformed spec, quoted placeholder in historical evidence, inaccessible path and unknown base. Only explicit template markers/typed fields trigger findings; arbitrary prose containing `TODO` must not fail.
2. Add status JSON fields for findings, branch/HEAD/base, dirty product paths and observation time. Missing Git/base yields `unknown`, not zero-ahead. Never read secrets, unbounded logs or arbitrary symlink destinations while scanning evidence.
3. Populate the start template's evidence README with change ID, route, branch/HEAD and `draft; implementation not started`. At the first implementation transition append a small WIP checkpoint naming product-diff state. Use the existing transition mechanism; do not add a daemon. Record evidence obligations as `not_run` with reason until measured rows exist.
4. Surface concise findings in `stop_gate.py` and before review-receipt recording where mandatory evidence is actually required. Quoted historical failures do not block unrelated current evidence. Keep fail/pass receipt schema unchanged.
5. Verify fixture status output detects the zero-ahead dirty case, preserves drafts, identifies missing mandatory rows, and does not mutate the tree. Pair with #54 doctor fields instead of making a second all-worktree crawler.

Files: `scripts/grok_status.py`, `.grok-stack/adaptive_grok/change.py`, existing spec helpers, `.grok-stack/templates/change/{evidence/README.md,state.json}`, `.grok/hooks/stop_gate.py`, `scripts/grok_review.py`; `tests/test_change_receipts.py`, `tests/test_change_spec.py`, status/CLI fixtures. Coordinate with PR141/#125 completeness coverage and PR134 evidence-claim handling.

## Limits, gates, recovery

No new human approval is required for ordinary routed source implementation unless its selected route names one. Normal product verification, independent reviews and exact external merge check still apply. Checkpointing locally does not publish anything. A fresh clone cannot discover uncommitted local work; remote continuity requires an explicitly authorized committed/published WIP checkpoint. Do not auto-push or claim crash immunity.

Recovery: additive status fields can be ignored by older readers; retain previous observation rows and mark superseded rather than deleting evidence. Revert the diagnostic wiring/templates if needed; do not rewrite existing packages automatically.

Optional alternatives: a central cross-worktree index or periodic checkpoint service. Neither is required for this first same-worktree status feature. Turning every draft into a fatal error and banning all TODO text are rejected.

# Verification plan

Status: implementation not started; no implementation success is claimed.

First add failing comparator claimant/control regressions with exact status and reasons. Cover same-target agreement, nested paths/fragments, pure URN/HTTPS IDs, duplicate IDs and unsafe grammar. Preserve closure edge/scope tests and update only assertions relying on obsolete claimant-directed verdicts.

For diagnostics use repeated identical collisions in both inventories, then more than five distinct collisions; assert deterministic unique count, exact overflow count and independent per-referrer limits. Test empty/at-limit cases, out-of-scope silence, base-only nonfatal recovery, fatal head ID-only ambiguity encountered after many signals, and unrelated refusal visibility. Recheck shipped inventory without altering any contracts.

Focused commands: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_architecture_model.py'; repeat with test_architecture_fitness.py. Save actual red/green commands and results. No production or network effect is needed.

Coordinator runs python3 scripts/grok_verify.py --mode pr on the final tree, then dispatches code_reviewer and test_reviewer. Record actual reports and fingerprint-bound receipts under their existing exact kinds; do not relabel reviews. Schema-v2 references use verification/code_review/test_review only. Full local preflight never substitutes for the App-owned exact-PR-head Trust CI check.

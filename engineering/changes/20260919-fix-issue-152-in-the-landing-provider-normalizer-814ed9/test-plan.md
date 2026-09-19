# Risk-based verification

First observe the new diagnostic assertions fail on unmodified product code. Then run the provider, live-executor malformed-draft and backend persistence/receipt tests once after the patch. Cover controlled known failures, sensitive unknown details, invalid executor metadata, restart without replay, exact legacy receipt decoding, closed v1 projection and unchanged fallback refusal.

Root runs python3 scripts/grok_verify.py --mode pr against this worktree's own script once after product files are frozen, then records route-selected code/test/data reviews. A new source fix justified by a failure may require affected rechecks; status/documentation-only work does not justify a full rerun. No provider calls are part of source verification.

# Rollback plan — Codex SEO landing side project

## Trigger conditions

- Skill validation or focused contracts fail on the final tree.
- Showcase introduces an external first-load dependency or becomes indexable without a verified origin.
- Existing repository verification or Trust CI behavior regresses.
- License or exact upstream provenance cannot be demonstrated.

## Application rollback

Revert the side-project commit set in one change, removing the local skill,
showcase, focused tests, README additions, decision entry, and evidence. No data
migration or external system rollback is required.

## Data recovery / forward-fix

There is no persistent application data. Correct documentation or static files
in a forward fix only when the same exact review and verification gates can be
rerun; otherwise use the single revert.

## Verification after rollback

Confirm `.agents/skills/seo-landing/` and `side-projects/seo-landing-showcase/`
are absent, run `python3 scripts/grok_verify.py --mode pr`, and verify the
existing README graph and Trust CI behavior match the stacked base.

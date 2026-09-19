# Rollback plan — Prevent release intent from being masked by pull-request wording (#123)

## Trigger conditions

Rollback if explicit review requests cease routing to review, release intent loses its release controls when review wording co-occurs, generic feature tasks mentioning pull-request delivery are classified as review, or release-installer bugfixes stop retaining bugfix intent.

## Application rollback

This is a source-only router change with no runtime deployment, external write, or data migration. Revert the exact reviewed change commit in a follow-up source commit, restoring the previous router version. Do not rewrite route history or mutate active production state. Keep the reverted tree on the normal reviewed branch/pull-request path.

## Data recovery / forward-fix

No data recovery is needed. Previously persisted route artifacts remain historical evidence; new prompts will be classified by the restored router. If only one precedence edge is wrong, prefer a forward fix with paired full-control regressions for release+review, standalone review, generic PR wording, and release-installer bugfix.

## Verification after rollback

Run the focused router suite and the full selected PR checks on the reverted tree. Verify the four route behaviors above and confirm no route schema change. Bind current verification and review receipts to the reverted tree fingerprint. Any merge still requires the exact-head external Trust CI check and required signed scopes.

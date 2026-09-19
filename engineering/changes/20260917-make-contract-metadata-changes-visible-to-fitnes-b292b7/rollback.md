# Rollback plan — Make contract metadata changes visible to fitness (#120)

## Trigger conditions

Revert if metadata-only root edits are missed or mislabeled as wire incompatibility, unchanged schemas gain findings, structural comparisons regress, registered API YAML stops being checked, or change-package YAML continues to generate contract-structure findings.

## Application rollback

This change has no live runtime deployment or external state to roll back. Revert the repository source through a reviewed follow-up commit. Preserve the change package and verifier/review evidence for diagnosis; do not alter deployed Trust CI policy or attestations.

## Data recovery / forward-fix

No data migration or production record changes are involved. Prefer a forward fix when it can preserve the approved root-only metadata scope and existing structural/event semantics. If rolling back the selector fix independently, ensure package metadata still does not cause false contract findings before treating verification as meaningful.

## Verification after rollback

Run the focused architecture comparator and contract-selector regressions, `python3 scripts/grok_verify.py --mode pr`, and the route-selected review set on the reverted tree. Confirm all receipts bind to its final fingerprint. For delivery, independently confirm the App-owned Trust CI result and required signed scopes on the exact PR head.

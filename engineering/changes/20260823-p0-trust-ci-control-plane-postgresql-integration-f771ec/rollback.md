# Rollback

- Product repairs on `feat/trust-ci-control-plane` roll back by reverting the activation commits; do not force-push `main`.
- Deployed images/policy/holdout roll back to the previous reviewed digests; a policy/holdout rollback changes the policy epoch and requires fresh jobs.
- If the service is down and repository access must be restored: enable kill switch, retain PostgreSQL and attestations, use a human admin token to remove only the exact required policy-epoch check, repair, prove the check again, reapply protection.
- Never replace the external gate with a local receipt, delegated grant, or forged check.

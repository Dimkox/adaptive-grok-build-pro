# Rollback

Set GROK_TEST_WORKERS=0 for an explicit serial unittest run with the same configured coverage gate. A code rollback is a separate reverting pull request; never replace a failed parallel result with an unreported automatic retry.

For Trust CI use `GROK_TEST_WORKERS=0 make trust-ci-test`; it preserves full discovery and explicit DB skips. Reverting the PR restores original entrypoints; rolling back an independently deployed runner image is a separate operator action under external policy.

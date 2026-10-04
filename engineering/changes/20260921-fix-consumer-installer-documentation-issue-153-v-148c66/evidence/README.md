# Candidate evidence

33 focused installer tests pass; both artifact portability and relocation controls now satisfy renewed independent review. Historical first-review findings are retained in the `*-review-first.md` reports. [Candidate verification history](candidate-verification-history.json) binds product hashes and renewed reports while preserving the initial full gate as historical.

The final candidate must pass `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, then receive fresh selected review receipts. Final raw output and publication evidence are kept under `<local-path>` and summarized in the PR; local evidence supplies no external merge authority.

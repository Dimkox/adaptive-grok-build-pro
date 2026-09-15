# Verification

Run existing tests/test_project_state.py and tests/test_structure.py against corrected state and immutable graph/history. Update assertions that enforce obsolete current facts; add only meaningful cross-document inconsistency coverage if needed. Run required grok_verify --mode pr with UV_FROZEN=1 to keep dependency lockfiles stable. Selected independent code_reviewer inspects final diff and facts; record current fingerprint-bound receipts. External Trust CI remains merge authority.

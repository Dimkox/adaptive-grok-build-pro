# Combined verification

Existing measured RED/GREEN histories establish each defect and repair; do not invent a new failing integration result. Check exact source blob parity, then run the mandatory full PR verifier on the combined current-main tree in the single allocated CPU lane. It must cover root units/coverage, architecture/contracts, installed consumer checks and disposable PostgreSQL tier including166. Five selected code/test/security/release/data reviewers inspect the verified combined diff and its actual surroundings. Freeze reports/handoff, run final current-tree verification where the fingerprint requires it, record all exact receipts and check zero gaps before publication.

Any observed integration failure goes to the sole writer for diagnosis/minimal repair and focused RED/GREEN evidence. Never overlap this heavy lane with sibling local gates or external CI.

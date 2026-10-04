# Pre-cutover observation

Target installed interpreter: 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960. pip check exit 0; dependency inventory matches both old runtimes after preserving idna 3.19. Installed Python package sources match the merged source. Focused migration/restart/backup checks: 19 passed, 1.258s, process exit 0. Operator scripts parse successfully; no product code change or full verifier repetition. Activation has not begun.

Subsequent cutover and rollback results are in acceptance-results.json and final-runtime.json.

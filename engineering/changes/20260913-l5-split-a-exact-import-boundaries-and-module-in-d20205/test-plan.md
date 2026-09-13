# Test plan

Baseline: 163 existing architecture/model tests pass on 4b3ad5e before extraction. Port existing meaningful regressions first and preserve their red result before copying the checker. Run focused checks, then prescribed grok_verify --mode pr and independent code/test reviews. Use 28-worker supplemental suites where useful; do not change the mandatory verifier.

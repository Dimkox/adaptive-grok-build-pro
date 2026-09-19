# Integration analysis — issue #125

Trust CI's independent source parser (`trust-ci/src/adaptive_trust_ci/runner.py`) and holdout validate AC/INV/FORBID records for shape and duplicate IDs, but currently derive signed `criterion_coverage` from AC only; its model accepts AC-only IDs. Extending the signed denominator requires coordinated parser/model/contract changes and later deployment outside this PR. Existing signed raw payload verification preserves AC-only signatures.

# M4→M9 dependency ledger

| Milestone | Input required by M8 | Current fact | M8 treatment |
| --- | --- | --- | --- |
| M4 | exact control-plane identity | source base `9fe779ab9f90719201acfd01160d3452658ff075`; local unpushed candidate `aee6558bb83418d7a1acb4582df6845bf7bdc3c6` | opaque identity only; acceptance blocked |
| M5 | accepted execution-profile digest | committed provisional `161199bb163e0ba84ac1b32010be87f113df5e86`; concurrent Task 6 docs/architecture work dirty | opaque identity only; acceptance blocked |
| M6 | accepted validator-profile digest | committed provisional `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` | opaque identity only; acceptance blocked |
| M7 | accepted exact head, shadow bundle, real human decisions | committed provisional evaluator `030a8d7a03a3b1da9d0ad5bcf1548910cb5f679c`; concurrent `test_shadow_contracts.py` plus `factory/contracts/jsonschema/` work dirty; no factual cohort here | source-only shape reference; factual qualification blocked |
| M8 | exact tuple/profile/recommendation/demotion | design checkpoint `7feedf4577953985b3137a1caeea28bdca70a61e`; pure source explicitly allowed | recommendation-only, L2 ceiling; activation blocked |
| M9 | exact signed delivery/recovery outcomes | roadmap only | no delivery authority; future feedback only |

No row is an attestation or acceptance record. Historical evidence packages are untouched.

The 2026-09-02 pre-implementation audit found zero overlap between the four planned M8 product paths and committed M4/M5/M6/M7 deltas from `9fe779ab9f90719201acfd01160d3452658ff075`; the concurrent M5 and M7 dirty paths also have zero product-path overlap. Every M8 commit must repeat the exact upstream-head and overlap check.

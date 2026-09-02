# M4→M9 dependency ledger

| Milestone | Input required by M8 | Current fact | M8 treatment |
| --- | --- | --- | --- |
| M4 | exact control-plane identity | source base `9fe779ab9f90719201acfd01160d3452658ff075`; local unpushed verification candidate `d31a4ade4a38a334df01fb405a5696e5660993df` | opaque identity only; acceptance blocked |
| M5 | accepted execution-profile digest | committed provisional source-map head `141e51e75b2bb337fa3bb1544639c6c46c287309`; concurrent verification/package updates dirty | opaque identity only; acceptance blocked |
| M6 | accepted validator-profile digest | clean provisional M5-aligned merge `c398ea06daa635ad679e22c8cd29dbf74d2ae12c` | opaque identity only; acceptance blocked |
| M7 | accepted exact head, shadow bundle, real human decisions | clean provisional source/docs head `c8b450f494b3d44b580556c6a612b21a3a780368`; two architecture-drift paths remain and no factual cohort exists | source-only shape reference; factual qualification blocked |
| M8 | exact tuple/profile/recommendation/demotion | source-only override checkpoint `0e7d7558ebb603c0e5c914beefe01397321151b4`; pure source explicitly allowed | recommendation-only, L2 ceiling; activation blocked |
| M9 | exact signed delivery/recovery outcomes | roadmap only | no delivery authority; future feedback only |

No row is an attestation or acceptance record. Historical evidence packages are untouched.

The 2026-09-02 pre-implementation audit found zero overlap between the four planned M8 product paths and committed M4/M5/M6/M7 deltas from `9fe779ab9f90719201acfd01160d3452658ff075`; the concurrent M5 dirty paths also have zero product-path overlap. Every M8 commit must repeat the exact upstream-head and overlap check and abort if any observed head differs from the expected value.

# M9 Evidence and Blocker Ledger

| Item | State | Required evidence / owner | Invalidated by |
| --- | --- | --- | --- |
| route and source checkpoint | present | route `e376373492fe`; Git base `9fe779ab9f90719201acfd01160d3452658ff075` | source-base change |
| scope/design approval | present for Tasks 1–4 source only | explicit 2026-09-02 user ruling permits pure local source/tests with synthetic opaque exact identities | requested scope/design change |
| provisional dependency observations | present / unaccepted | M4 `da7ec8d7d40f52663aba1ff59bf03ccf209395b0` local verifier-pass but unreviewed; M5 `141e51e75b2bb337fa3bb1544639c6c46c287309`; M6 `3def83eb915ca68e66379269526ffa64822a1104`; M7 `c8b450f494b3d44b580556c6a612b21a3a780368`; M8 Task-1 source `5735e762b8d7571887f6fa4ac9cf10cd1fad1954` | any predecessor change or contrary review |
| accepted M4→M8 chain | `BLOCKED` | dependency-ordered accepted exact SHAs and external exact-head gates; milestone owners | any predecessor change |
| accepted M8 profile/cohort | `BLOCKED` | factual durable profile/cohort digests and qualifying evidence; M8/human owner | tuple/policy/evidence change or demotion |
| signed artifact inputs | `BLOCKED` | exact merged SHA, artifact, SBOM, provenance, manifest, image and externally verified opaque authority | any digest/SHA/authority expiry change |
| prior signed artifact | `BLOCKED` | exact externally verified artifact eligible for restore | mismatch, expiry or resource change |
| nonproduction environment | `BLOCKED` | named separately authorized preview/staging/canary resource set and observation source | environment/policy/authorization change |
| exercised recovery | `BLOCKED` | observed restoration of exact prior signed artifact in authorized nonproduction environment | artifact/environment/policy change |
| source-only Tasks 1–4 | authorized / not started | strict TDD against synthetic opaque identities; sole `ai_implementer` write owner | any design/scope change |
| Task 5 integration | `BLOCKED` | separately opened task after applicable source and dependency gates | any source/design/restack change |
| local verification/reviews | not started | verification, code, test, security, release receipts on final source fingerprint | any repository change |
| PR/external Trust CI | not authorized | separate delegated branch/PR operations and App-owned check on exact head | new head/base/policy/holdout |
| production | human-only / unreachable | separate human decision and external operational authority | always outside this route |

No row may be changed from `BLOCKED` based on an example, placeholder, synthetic fixture, prose claim or locally minted value. Passing Tasks 1–4 proves source behavior only.

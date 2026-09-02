# M9 Evidence and Blocker Ledger

| Item | State | Required evidence / owner | Invalidated by |
| --- | --- | --- | --- |
| route and source checkpoint | present | route `e376373492fe`; Git base `9fe779ab9f90719201acfd01160d3452658ff075` | source-base change |
| scope/design approval | present for documentation checkpoint | explicit user approval of canonical design | requested scope/design change |
| accepted M4→M8 chain | `BLOCKED` | dependency-ordered accepted exact SHAs and external exact-head gates; milestone owners | any predecessor change |
| accepted M8 profile/cohort | `BLOCKED` | factual durable profile/cohort digests and qualifying evidence; M8/human owner | tuple/policy/evidence change or demotion |
| signed artifact inputs | `BLOCKED` | exact merged SHA, artifact, SBOM, provenance, manifest, image and externally verified opaque authority | any digest/SHA/authority expiry change |
| prior signed artifact | `BLOCKED` | exact externally verified artifact eligible for restore | mismatch, expiry or resource change |
| nonproduction environment | `BLOCKED` | named separately authorized preview/staging/canary resource set and observation source | environment/policy/authorization change |
| exercised recovery | `BLOCKED` | observed restoration of exact prior signed artifact in authorized nonproduction environment | artifact/environment/policy change |
| product implementation | not started | TDD plan execution after factual accepted M8 restack | any design/restack change |
| local verification/reviews | not started | verification, code, test, security, release receipts on final source fingerprint | any repository change |
| PR/external Trust CI | not authorized | separate delegated branch/PR operations and App-owned check on exact head | new head/base/policy/holdout |
| production | human-only / unreachable | separate human decision and external operational authority | always outside this route |

No row may be changed from `BLOCKED` based on an example, placeholder, fixture, prose claim or locally minted value.

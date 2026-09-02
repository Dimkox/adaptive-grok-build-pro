# M9 Evidence and Blocker Ledger

| Item | State | Required evidence / owner | Invalidated by |
| --- | --- | --- | --- |
| route and source checkpoint | present | route `e376373492fe`; Git base `9fe779ab9f90719201acfd01160d3452658ff075` | source-base change |
| scope/design approval | present for Tasks 1–4 source only | explicit 2026-09-02 user ruling permits pure local source/tests with synthetic typed identities and no external action | requested scope/design change |
| provisional M8 producer observation | present / unaccepted | M8 `2cee9b93c161b6c76f4fee877e6d19eacee5a271`; its embedded M7 producer reference is `4df2516fa3a137fa730d08733fb9e338768232fb` and remains blocked pending durable lookup | any predecessor/source change or contrary review |
| accepted M4→M8 chain | `BLOCKED` | dependency-ordered accepted exact SHAs and external exact-head gates; milestone owners | any predecessor change |
| accepted/current M8 profile/cohort | `BLOCKED` | server-derived durable acceptance/currentness for the exact typed tuple/cohort/profile/recommendation; M8/human owner | tuple/policy/evidence change, expiry or demotion |
| signed artifact inputs | `BLOCKED` | exact merged SHA, artifact, SBOM, provenance, manifest, image and externally verified opaque authority | any digest/SHA/authority expiry change |
| prior signed artifact | `BLOCKED` | exact externally verified artifact eligible for restore | mismatch, expiry or resource change |
| nonproduction environment | `BLOCKED` | named separately authorized preview/staging/canary resource set and observation source | environment/policy/authorization change |
| trusted controller clock | `BLOCKED` | operator-owned clock/source binding for evaluation and record time; Task 5 owner | clock source or policy change |
| trusted restart witness | `BLOCKED` | trusted checkpoint or complete independently witnessed observations, decisions and recoveries; Task 5 owner | chain/input/checkpoint change |
| exercised recovery | `BLOCKED` | observed restoration of exact prior signed artifact in authorized nonproduction environment | artifact/environment/policy change |
| source-only Tasks 1–4 plus M8 boundary correction | implemented locally on provisional base; not accepted or activated | initial 67 tests plus typed-boundary regressions; old opaque digest pair reproduced an unauthorized source-conformance `advance`, then typed equality/aggregate/lifecycle/resource tests turned GREEN. Against exact M8 `2cee9b9`, the canonical blocked fixture yields `m7_bundle_blocked` with no existing profile and `cohort_replay` only when the same cohort is supplied as the existing profile; both are non-authorizing and both are denied by M9. Cohort/profile/recommendation digests match the producer in the corresponding replay check; sole `ai_implementer` write owner | any contract/design/scope/predecessor change |
| provisional architecture ownership | present / non-authoritative | `NODE-STAGED-DELIVERY-SOURCE` owns current `delivery` source/tests and has only a no-network filesystem verification edge; exact `.venv` directories use the bounded tooling-cache exclusion while lookalikes remain inventoried | source/path/edge/rule change |
| durable M8 boundary resolver | `BLOCKED` | current adapter is code-owned `blocked_pending_durable_m8_lookup` with no caller override and must be deleted on factual restack | accepted M8 source/currentness change |
| Task 5 factual integration | `BLOCKED` | direct M8 imports, durable currentness resolver, machine-readable delivery schemas, repository-wide status docs, runtime wiring and activation require a separately opened task after applicable source and dependency gates | any source/design/restack change |
| local verification/reviews | pre-commit checks only / no receipts; independent reviews not started | targeted and full `--no-record` verification are non-authoritative preflight and must match the final tree; code, test, security and release reviews plus route-requested receipts remain for the factual restack | any repository change |
| PR/external Trust CI | not authorized | separate delegated branch/PR operations and App-owned check on exact head | new head/base/policy/holdout |
| production | human-only / unreachable | separate human decision and external operational authority | always outside this route |

No row may be changed from `BLOCKED` based on an example, placeholder, synthetic fixture, prose claim or locally minted value. Passing Tasks 1–4 proves source behavior only.

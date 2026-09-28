# Engineering economics — issue #218 delivery

## Time and salary assumptions

- User-reported elapsed checkpoint: approximately **7 hours 45 minutes** (`7.75` wall-clock hours). This is a rounded user observation, not reconstructed agent-active time.
- Salary assumption supplied by the user: `$360,000/year ÷ 2,080 hours/year = $173.0769/hour`, rounded to **$173.08/hour**.
- Wall-equivalent salary cost at that checkpoint: `7.75 × $173.08 = $1,341.37`, reported as approximately **$1,341**.
- Parallel-equivalent effort estimate: **10–12 person-hours**, or approximately **$1,731–$2,077** at the same hourly rate (`10 × $173.08` through `12 × $173.08`). This range is an estimate, not an exact accounting of agent-hours.
- All salary-equivalent figures exclude employer taxes, benefits, equipment, infrastructure, model/API, and other overhead.

Exact agent-active hours are unavailable. Parallel agent execution, waiting time, coordinator time, repeated verification, and prior development-route work cannot be reliably reconstructed from wall time alone.

## Route timing

- Delivery route `566746aef130` created: **2026-09-25T20:03:20Z**.
- Delivery-route closure: **pending** as of this evidence update; no closure timestamp or final route-local duration is claimed.
- The user-reported 7h45m checkpoint covers the broader issue effort and must not be inferred from the later delivery-route creation time.

## Recorded expensive checks

| Activity | Recorded duration/result | Classification |
| --- | --- | --- |
| First generated-package/receipt compatibility affected-module contour | 91.22s; 78 tests and 116 subtests passed after repair | Compatibility churn that was necessary to align legacy fixtures/templates with the new contract |
| First exact-head pre-review verifier | Core 78.590s; Factory PostgreSQL 193.585s; PASS | Useful full confidence run before independent review |
| Full-core compatibility rerun | 66.87s; 1,002 passed and two stale diagnostic assertions failed | Compatibility churn; product confidentiality behavior was already correct |
| Full verification-doctor module | 209.51s; 121 tests and 65 subtests passed | Compatibility confirmation; expensive relative to the two changed assertions |
| Second exact-head verifier on `ddd9988e...` | Core 83.888s; Factory PostgreSQL 190.977s; PASS | Useful exact-head verification before bounded re-review |
| Current I-1 focused contours | 1.49s adversarial; 6.38s diff/history; 7.44s util; 3.37s receipts; all PASS | Useful focused RED/GREEN confirmation before another full run |
| Final `de23e5da` review repair | RED 1.004s; first GREEN 1.019s; aggregate/endpoint budget 0.179s; final hostile/history contour 4.260s | Review-triggered assurance churn that removed a measured quadratic CPU path and restored legacy compatibility |
| Final `f2789117` review repair | RED 0.625s; first GREEN 0.648s; two wiring-mutant REDs 0.222s/0.193s; focused contour 4.896s | Review-triggered correctness and test-strengthening churn for maximum stable anchors and aggregate budget wiring |

The initial full-suite attempt that found generated-template and scanless-fixture incompatibilities is recorded in implementation evidence, but its complete wall duration was not captured; no duration is invented here.

## Value delivered versus churn

Useful security findings closed real local-evidence bypasses: forged scan counters, inherited Git controls, repository-local worktree redirection, repository-controlled whitespace policy, unsupported object types and file races, and raw diagnostic disclosure. These findings materially strengthened exact-root, full-chain, fail-closed, and no-secret guarantees.

Compatibility churn came from generated template whitespace, legacy tests fabricating now-invalid receipts, a removed compatibility constant, fixed-position Git argv mocks, and assertions that expected raw diagnostics after redaction. Those repairs were necessary for compatibility but did not themselves add new security coverage; earlier whole-module/full-gate runs could have found them in fewer cycles.

The final review of `de23e5da` added another useful security finding and another compatibility correction: repetitive inputs exposed unbudgeted quadratic comparison cost, while changed clean context exposed a legacy bad-line false positive. The package-inventory correction is evidence churn rather than product value. Route closure and its exact UTC/duration remain pending; this update does not invent later agent-hours or a final cost.

The `f2789117` reviews found one further compatibility false positive and two production-wiring test mutants. The maximum-monotone repair is useful correctness work; the additional review/evidence/amend cycle is assurance churn. Closure remains pending, so no closure timestamp, final duration, exact agent-hours, or revised salary-equivalent total is claimed.

## Recommendation for subsequent issue economics

Freeze a strict issue acceptance boundary before implementation. Run focused RED/GREEN checks first, budget one full pre-review run and one final recording run, and expand the work only for a reproducible Critical or Important finding within that issue's trust boundary. Track route start, focused/full command durations, compatibility-only reruns, review-triggered security work, and closure time separately so later cost estimates do not conflate useful assurance with workflow churn.

# M4→M9 dependency ledger

| Milestone | Input required by M8 | Current fact | M8 treatment |
| --- | --- | --- | --- |
| M4 | exact control-plane intent/lease identity | carried in each full M7 bundle and recomputed by the temporary reader | wire fact only; acceptance remains external |
| M5 | exact execution packet/manifest/snapshot/result identities and input/result heads | carried in each full M7 bundle; external M5 currentness/acceptance is not an M8 payload field | wire fact only; acceptance remains external |
| M6 | exact envelope/binding/validation-input/subject/evidence-set/verdict identities and closed pass verdict | carried in each full M7 bundle; latest independently observed provisional successor is `2d2360cd6f2a19ad3328d468073a52927691b112` | wire fact only; acceptance remains external |
| M7 | exact bundle(s), outcomes, cohort and recomputed evaluation | provisional producer checkpoint `4df2516fa3a137fa730d08733fb9e338768232fb`; all bundles are `blocked_pending_durable_lookup`, with no durable acceptance/currentness result and no factual 30-row cohort claim | full bounded wire reference; qualification blocked |
| M8 | exact tuple/profile/recommendation/demotion | correction starts from `5499c582d403c6955324b935cbb8799b38257f5f`; synthetic fixtures only | recommendation-only, L2 ceiling; factual profile acceptance and activation blocked |
| M9 | exact signed delivery/recovery outcomes | provisional sibling checkpoint `dffb188de5b8affb8f6644f0c22068f6f703e6b5`; not restacked on this correction | no delivery authority; future feedback only |

No row is an attestation or acceptance record. Historical evidence packages are untouched.

The bounded adapter exists only because this branch lacks M7 ancestry. Factual M7 restack must delete it and import the producer contracts plus durable lookup; retaining two implementations is forbidden. No row above is an attestation or acceptance record.

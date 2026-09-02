# M4→M9 Connectivity

| Edge | Required exact producer output | Current factual state | Consumer rule |
| --- | --- | --- | --- |
| M4→M5 | accepted frozen task packet and M4 exact SHA | provisional M4 source base `9fe779ab9f90719201acfd01160d3452658ff075`; acceptance not claimed | M5 must restack and bind exact accepted packet/SHA |
| M5→M6 | accepted execution-result/run-manifest digest and exact head | provisional M5 branch is known from roadmap; no accepted identity in this package | M6 rejects any different packet/artifact/image/policy binding |
| M6→M7 | accepted independent semantic verdict bound to exact head/findings | provisional M6 branch is known from roadmap; no accepted identity in this package | M7 cannot create ready-for-PR state without matching PASS and checks |
| M7→M8 | immutable shadow bundle with human decision and outcome metrics | roadmap only; no factual accepted bundle/cohort | M8 cohort tuple starts fresh on any component change |
| M8→M9 | accepted profile/cohort bound to repository/class/models/prompts/tools/policy/runner/holdout | `BLOCKED`: no factual accepted M8 restack/profile/cohort | M9 refuses construction/evaluation until exact identities are supplied |
| M9 source→activation | exact merged SHA plus artifact/SBOM/provenance/manifest/image and opaque external authority; authorized environment and prior artifact | `BLOCKED`: no signed input or environment/recovery proof | activation remains separate; production always human-owned |

Every predecessor change invalidates downstream evidence and requires restack/reissue. Repository docs, fixtures, local receipts and calendar dates cannot manufacture a producer output. Rollback moves only backward: quarantine/supersede evidence, halt/decrease exposure/restore exact prior artifact, preserve audit and demote profile.

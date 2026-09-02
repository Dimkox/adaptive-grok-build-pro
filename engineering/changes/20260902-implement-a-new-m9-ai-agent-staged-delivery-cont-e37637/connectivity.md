# M4→M9 Connectivity

| Edge | Required exact producer output | Current factual state | Consumer rule |
| --- | --- | --- | --- |
| M4→M5 | accepted frozen task packet and M4 exact SHA | base is `9fe779ab9f90719201acfd01160d3452658ff075`; provisional M4 `da7ec8d7d40f52663aba1ff59bf03ccf209395b0` is local verifier-pass but unreviewed | M5 must restack and bind exact accepted packet/SHA |
| M5→M6 | accepted execution-result/run-manifest digest and exact head | provisional M5 `141e51e75b2bb337fa3bb1544639c6c46c287309`; unaccepted | M6 rejects any different packet/artifact/image/policy binding |
| M6→M7 | accepted independent semantic verdict bound to exact head/findings | provisional M6 `3def83eb915ca68e66379269526ffa64822a1104`; unaccepted | M7 cannot create ready-for-PR state without matching PASS and checks |
| M7→M8 | immutable shadow bundle with human decision and outcome metrics | provisional M7 `c8b450f494b3d44b580556c6a612b21a3a780368`; unaccepted | M8 cohort tuple starts fresh on any component change |
| M8→M9 | accepted profile/cohort bound to repository/class/models/prompts/tools/policy/runner/holdout | `BLOCKED`: provisional M8 Task-1 source `5735e762b8d7571887f6fa4ac9cf10cd1fad1954` is not a factual accepted restack/profile/cohort | Tasks 1–4 may test closed bindings with synthetic opaque identities; acceptance and activation require exact factual identities |
| M9 source→activation | exact merged SHA plus artifact/SBOM/provenance/manifest/image and opaque external authority; authorized environment and prior artifact | `BLOCKED`: no signed input or environment/recovery proof | activation remains separate; production always human-owned |

Every predecessor change invalidates downstream evidence and requires restack/reissue. Repository docs, fixtures, local receipts and calendar dates cannot manufacture a producer output. Rollback moves only backward: quarantine/supersede evidence, halt/decrease exposure/restore exact prior artifact, preserve audit and demote profile.

# M4→M9 Connectivity

| Edge | Required exact producer output | Current factual state | Consumer rule |
| --- | --- | --- | --- |
| M4→M5 | accepted frozen task packet and M4 exact SHA | base is `9fe779ab9f90719201acfd01160d3452658ff075`; provisional M4 `da7ec8d7d40f52663aba1ff59bf03ccf209395b0` is local verifier-pass but unreviewed | M5 must restack and bind exact accepted packet/SHA |
| M5→M6 | accepted execution-result/run-manifest digest and exact head | provisional M5 `141e51e75b2bb337fa3bb1544639c6c46c287309`; unaccepted | M6 rejects any different packet/artifact/image/policy binding |
| M6→M7 | accepted independent semantic verdict bound to exact head/findings | latest independently observed provisional M6 successor `2d2360cd6f2a19ad3328d468073a52927691b112`; unaccepted | M7 cannot create ready-for-PR state without matching PASS and checks |
| M7→M8 | immutable shadow bundle with human decision and outcome metrics | provisional M7 correction `4df2516fa3a137fa730d08733fb9e338768232fb`; bundles remain blocked pending durable lookup | M8 cohort tuple starts fresh on any component change |
| M8→M9 | typed profile/cohort/recommendation bound to repository/class/M7 key/provider mapping/agent/validator/provider/model/prompt/policy/runner/holdout | `BLOCKED`: provisional M8 correction `2cee9b93c161b6c76f4fee877e6d19eacee5a271` is pinned by a temporary digest-compatible adapter, but its M7 bundles remain blocked and no durable accepted/current profile exists | Tasks 1–4 may test linked synthetic typed bodies; Task 5 must delete the adapter after factual restack and use server-derived currentness |
| M9 source→activation | exact merged SHA plus artifact/SBOM/provenance/manifest/image and opaque external authority; authorized environment and prior artifact | `BLOCKED`: no signed input or environment/recovery proof | activation remains separate; production always human-owned |

Every predecessor change invalidates downstream evidence and requires restack/reissue. Repository docs, fixtures, local receipts and calendar dates cannot manufacture a producer output. Rollback moves only backward: quarantine/supersede evidence, halt/decrease exposure/restore exact prior artifact, preserve audit and demote profile.

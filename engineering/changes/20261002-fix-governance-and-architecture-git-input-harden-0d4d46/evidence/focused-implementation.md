# E implementation focused evidence

Route: 0d4d463121b2. Branch: fix/v211-governance-inputs. Implementation base: e5856acfd4bc7a186f40a740b54ec86459462db5. Sole selected writer: general_implementer. Historical adaptive-grok-build-pro-m3 was read-only intent/source material, with no imports of old receipts or aggregate commits.

Product inventory is exactly:

- .grok-stack/adaptive_grok/architecture_diff.py
- .grok-stack/adaptive_grok/governance.py
- scripts/grok_governance.py
- tests/test_governance.py

Initial boundary RED command, `env PYTHONPATH=tests python3 -m unittest test_governance.GovernanceInputBoundaryTests -v`, ran 12 tests in 0.815 s and produced 7 failures/11 subtest errors. Causes were an actual foreign ambient Git head, lack of explicit binding, wrong-format rejection, executed replacement bytes, late/unbounded governance Git output and absent pinned projection/budget guards. The new missing APIs account for the reported errors; the Gitlink characterization already passed on the stronger current implementation.

The later four-control RED command covered repository-authored active rule authority, late authority mutation hidden by assume-unchanged, projection symlink acceptance and mutation during payload assembly. All four failed before repair, then passed in 6.874 s. Linked registration-after-read mutation, linked/ordinary common-directory redirects and continued reads after byte exhaustion each failed separately before the corresponding guard.

Final focused commands/results on the pre-commit candidate:

| Command | Result |
| --- | --- |
| taskset -c 10 env PYTHONPATH=tests python3 -m unittest test_governance test_governance_fitness | 83 tests, 93.051 s, OK |
| taskset -c 11 env PYTHONPATH=tests python3 -m unittest test_architecture_fitness | 131 tests, 132.197 s, OK |
| taskset -c 10 env PYTHONPATH=tests python3 -m unittest test_governance.GovernanceInputBoundaryTests -v | 19 tests, 1.237 s, OK; includes the final real character-device descriptor characterization |
| git diff --check | exit 0 |

Intermediate full focused runs exposed a repeated-observation test needing one separate publication recheck, streamed setup error context, and a generic exception translation that broke the existing uncaught-runtime/child-cleanup characterization. Those were repaired and all named cases are included in the final successful focused runs. No failing test is omitted from this handoff.

Bounds/compatibility: controlled explicit Git directory/worktree and common-directory relationship, full supported commit-format identity, disabled replacement reads, configured-filter refusal before status, raw regular blob reads, existing capped process deadlines/output, 16 MB shared unique consumed-input retention, descriptor-pinned fixed regular projection bytes and final mutation checks. Existing successful JSON shape, authority topology, clean worktree, current HEAD and SHA-1 GovernanceHandoffV1 stay intact. SHA-256 architecture helpers pass real-object tests; frozen v1 handoff refuses SHA-256 explicitly. Direct device-node creation is not exercised; an actual /dev/null descriptor is refused by the reused pinned reader. Unregistered Git pointer roots fail closed.

The controller must refresh the actual agreed origin/main base and run full PR verification/reviews on the exact final committed candidate. These focused observations are historical after any commit/base/tree change and confer no external merge/publication authority.

The scoped implementation was committed as d710ef6bf. After a clean status and fetch, actual origin/main 63799f8760d3a55028d83ab5ff0116ececf8f7d1 was integrated by merge 632afd064fa5151338225815b1418d416477d552 without conflicts. `git diff --exit-code d710ef6bf HEAD -- .grok-stack/adaptive_grok/architecture_diff.py .grok-stack/adaptive_grok/governance.py scripts/grok_governance.py tests/test_governance.py` returned 0: integration changed none of these four scoped product bytes. Relative to the agreed main base, inventory remains the four product files plus this package. `git diff --check origin/main HEAD` returned 0, and no protected branch, old worktree, tag, release or deployed state was written.

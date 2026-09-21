# Exact candidate import

Route `bcc1d645c438`; sole selected writer `integration_implementer`; 2026-09-21.
Worktree `/home/pall/grok-projects/adaptive-grok-build-reviewed-batch`, branch `fix/reviewed-issues-batch-20260921`.
Import started at HEAD `1146cee355ab9dd9d1db9bbb357a11bd4e4cc8b5` against delivered main `839d3aa26bc90417424d814ee48d8b5cd3be367e`.

## Result and source identity

Imported exactly the 19 declared product/test paths from six pinned candidate commits, plus their six complete historical change packages and the accepted ingress package from `07b2dd2f103abc3235f38a523a558b60a40d4034`. The seven packages contain 188 files, making 207 exact imported files. Every imported file's Git blob, Git mode and SHA-256 matches its source object in both the index and working tree; each package's staged Git tree matches its original package tree. No integration product correction was necessary.

The complete per-file identity record is [integration-source-identity.json](integration-source-identity.json), SHA-256 `25359b37630956d3f2da85c9e06663cd3dc95a36f47aa6e33c8ee9fdc9c40275`. Its index tree `0baf1ec7ee7cbf845cf5e21a4de03df2bedbbb39` is the import observation before coordinator documentation synthesis and these new evidence files; it is not a final commit or repository fingerprint.

| Source slice | Exact candidate commit | Product/test paths | Historical package tree |
| --- | --- | --- | --- |
| Router #156 | `08a16f8c5278109c03762082be1d11775ead04b8` | 4 | `4d2a550aa562c714ede6ec69583885587e3815ed` |
| Receipt schema #162 | `832e642ab868929bfd1a4a4c3a462ce6e7ea9072` | 2 | `f5a3e11639845ff808e483b151492d4b9eddebcd` |
| Consumer documents #153/#161 | `ac7c4ff14981ae462de804bd250520a1013cfd68` | 4 | `5a929c4c8d3106aabd3aee660636dbb6c1e4e89b` |
| Fingerprint #168 | `3ff6ed291243373871957b62929d40a264522e00` | 4 | `17055c0d350b422a98c0e4312520f23005252fac` |
| Schema references #147/#148 | `f04cb6cddd4a38db3fb022c9df48af0b9a808c6b` | 4 | `f2c8eb519477fef48e94587dcccde2548bd72f4a` |
| Migration prefix #166 | `23eb62dc21a090e6bf086cbc2a568d83417b0a2e` | 1 | `e0575484cac566d36ba9d30c3058a7c7065c2256` |
| Accepted ingress record | `07b2dd2f103abc3235f38a523a558b60a40d4034` | 0 | `abcf9d59a2d2bd9465036b92a211e54ee826b7bb` |

All six product sets also match the separately reviewed implementation commits recorded by the analyses and identity JSON. Existing successful and failed reviews, repair histories, original route identities, timestamps and scope limits remain verbatim. Historical local receipts have not been copied or relabeled as combined evidence.

## Performed operations

Read the repository entrypoints and contract, active route, all route-selected workflow skills, typed scope/design/verification/recovery plans, candidate manifest and all five analysis reports. Fetched remote refs and inspected the exact candidate deltas, source/test surfaces and Git inventories. The initial worktree and index were clean.

Materialized product paths in the adopted sequence: receipt schema, router/reader, architecture references, installer/templates, migration tests, then fingerprint/JSON utility. Each command used `git restore --source <full candidate SHA> --staged --worktree -- <explicit manifest product paths>`. A subsequent exact-path restore imported each named package from its source commit. No mutable candidate worktree was a copy source; no whole-branch cherry-pick, commit or ref update occurred. All 19 final source entries are regular `100644` files; this manifest has no product deletions.

A bounded metadata collector compared source Git objects, stage-zero index entries and the imported working files. SHA-256 hashes and Git blob hashes were independently calculated from actual bytes; path-status equality alone was not treated as content proof. Each package's complete disk inventory was also compared with its exact source file inventory. `git write-tree` created the local index tree object solely to compare package and protected subtree identities.

The first metadata collection attempt stopped before writing its report because `git ls-tree` rejects `:(glob)**/*.sql` pathspec magic. The corrected collector filters the full NUL-delimited tree metadata inventory for literal `.sql` suffixes. This correction changed no imported source or evidence package; both the cause and correction are retained in the identity JSON.

## Preserved boundaries

Main and the candidates' predecessor `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` both resolve to tree `e2a807845c77af0c6023c53fcd30972ede9fb8bd`. The 19 product paths are distinct; imported candidate source needs no base reconciliation.

Index and tracked-worktree diffs against main are empty for all SQL paths, `trust-ci/`, `.github/workflows/`, factory production source, the disposable runner/restart probe, architecture model/rules/generated views, `VERSION`, root `AGENTS.md`, routing/policy configuration and hook declarations. All 28 tracked SQL path/blob/mode entries match the base. The SQL resources subtree remains `7c95e0de1536b0cc5e790a9bb25992209bff8d3f`; the Trust CI subtree remains `3776b2df790b8330c8c660509b28df4729b4a5b3`. No GitHub workflow source exists in the base or imported index.

The coordinator owns README/bootstrap/project state, shared decisions/mistakes, active batch documentation and the separately retained research package; this writer has not edited them. The manifest may subsequently gain that documentation provenance without expanding these 19 product paths. No runtime receipts, grants, credentials, host changes, external operations, active #165/#163 source, migration022 or separate #162 Trust CI validator successor was imported.

## Verification and remaining work

Source identity checks passed. Tests, product imports, compilation, lint, Docker and database checks were not run: the shared CPU lane remains allocated by the coordinator. Existing exact-source RED/GREEN results stay historical; no new failing integration result was manufactured.

The coordinator must finish the shared handoff, run the real full combined PR verifier on the frozen tree, then obtain all five selected independent reviews and current fingerprint-bound receipts. The installer, fingerprint and schema-reference repairs still need that final combined gate. Fresh local evidence and the exact-head external App check with any required signed scopes remain prerequisites to delivery and issue closure. This import report is not a completion receipt or merge authority.

Recovery before delivery is confined to this isolated branch. Any delivered source reversal requires another reviewed PR preserving SQL001–021 and existing consumer ownership. Importing accepted ingress documentation performs no host rollout and authorizes no service rollback.

Shared-memory facts for the coordinator: exact-path extraction from immutable candidate commits preserves reviewed bytes when base trees match, while allowing shared handoffs to be reconciled once. Do not assume Git subcommands accept identical pathspec features; use literal NUL-delimited `ls-tree` inventories for metadata filtering and reserve glob pathspecs for commands that support them.

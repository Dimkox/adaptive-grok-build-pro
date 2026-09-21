# Exact-source integration inventory

Selected role: `repo_explorer`; route `bcc1d645c438`; 2026-09-21.
Scope: static Git-object inventory and interactions for the six candidates in `candidates.json`.
No product edits, tests, product imports, compilation, Docker, host operations, or external writes were performed.

## Base and manifest findings

The target base is `839d3aa26bc90417424d814ee48d8b5cd3be367e` (merged PR #170).
Its complete tree is identical to the candidates' predecessor `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`:
both resolve to tree `e2a807845c77af0c6023c53fcd30972ede9fb8bd`, and their name-status diff is empty.
Thus these imports need no predecessor-source reconciliation; the different commit identities still require new evidence binding.

All six name-status manifests match `candidates.json`: no missing product path and no undeclared path outside each listed handoff or change package.
There are **19 distinct product/test paths with zero cross-candidate path overlap**.
The only shared paths are `PROJECT_STATE.json`, `START_HERE.md`, `README.md`, `decisions.md`, and `mistakes.md`.
Each candidate's change-package directory is distinct.

| Candidate / issues | Exact candidate HEAD | Changed paths: product / handoff / package |
| --- | --- | --- |
| Router / #156 | `08a16f8c5278109c03762082be1d11775ead04b8` | 4 / 3 / 21 |
| Receipt schema / #162 | `832e642ab868929bfd1a4a4c3a462ce6e7ea9072` | 2 / 4 / 24 |
| Consumer documents / #153, #161 | `ac7c4ff14981ae462de804bd250520a1013cfd68` | 4 / 5 / 22 |
| Fingerprint / #168 | `3ff6ed291243373871957b62929d40a264522e00` | 4 / 5 / 25 |
| Schema references / #147, #148 | `f04cb6cddd4a38db3fb022c9df48af0b9a808c6b` | 4 / 5 / 23 |
| Migration prefix / #166 | `23eb62dc21a090e6bf086cbc2a568d83417b0a2e` | 1 / 4 / 23 |

The product sets consist exactly of the manifest's router/reader pair and tests; receipt schema/test; installer/two `.md.tmpl` inputs/test; fingerprint utility/verifier output/two tests; architecture/comparator fitness pair/two tests; and the single PostgreSQL test module.

## Reused review provenance

Read the actual candidate Git objects for each current code-review report, including the retained repair history described there.
For every row below, `git diff --exit-code <reviewed-product-commit> <candidate-head> -- <all product_paths>` returned 0 with no output.
This establishes exact reviewed-byte continuity, not a new combined verification result.

| Candidate | Reviewed product commit | Report inside its existing change package |
| --- | --- | --- |
| Router | `c58ddb7aaaaa594a3ad00d8667e4da09f750f3ca` | `evidence/code-review.md` |
| Receipt schema | `31c6b4e11c4554dbaa67943ec6156ec32633b111` | `evidence/code-review-schema-only.md` |
| Consumer documents | `8ef4625d5401556c7d2230c9f18cd0e0bc2c8852` | `evidence/code-review.md` |
| Fingerprint | `8278b2dd9b3fff69b5e408087c2e3b49a68e470c` | `evidence/code-review.md` |
| Schema references | `d19b1b687f24d9181d92ac8317fa74a961071548` | `evidence/code-review.md` |
| Migration prefix | `0558da4a4047ddf12114be33fb163b4e9124fdbf` | `evidence/code-review.md` |

## Protected-source boundary

For **every** candidate, the diff from target main is empty under `trust-ci/`, `:(glob)**/*.sql`, and `.github/workflows/`.
The complete manifest audit also excludes unlisted factory production changes: #166 changes only `factory/tests/test_execution_persistence_postgres.py`.
The separate #162 Trust CI validator successor and #163 migration 022 are absent from these net candidate trees.
Preserve source selection by final tree, including the schema-only #162 result after its abandoned mixed-source iteration.

The optional ingress documentation source `07b2dd2f103abc3235f38a523a558b60a40d4034` changes only its own package plus the five shared handoffs.
Its accepted-operation report is historical operational evidence, not authorization to repeat the operation.
Both that source and target main retain resource-tree `7c95e0de1536b0cc5e790a9bb25992209bff8d3f` and Trust CI tree `3776b2df790b8330c8c660509b28df4729b4a5b3`.

## Safe import sequence

The 19 product paths are disjoint, so their final union is order-independent. A practical sequence for the sole selected writer is:

1. Import the two receipt-schema paths from `832e642a…`.
2. Import the four router paths from `08a16f8c…`, keeping the optional producer field and bounded reader together.
3. Import all four schema-reference paths from `f04cb6cd…`, preserving comparator fallback and conservative closure together.
4. Import all four consumer-document paths from `ac7c4ff1…`, including both `.md.tmpl` inputs with the installer.
5. Import the PostgreSQL test module from `23eb62dc…` against the unchanged current SQL resources.
6. Import all four fingerprint paths from `3ff6ed29…` before generating any combined receipts or running verification.
7. Import the six existing packages and optional ingress package from their exact Git objects; reconcile the five shared handoffs once.

Use the full SHAs above and only each manifest's explicit paths, preserving file modes and exact bytes; do not copy mutable worktree contents.
After import, each candidate's product-path diff against the combined tree should be empty, and protected-source diffs against main should remain empty.
Preserve previous failed and repaired reviews as dated evidence; the combined package owns the new scope, outcome, and receipts.

## Interactions the combined gate must cover

- **Router ↔ fingerprint/state:** `router.py` calls `tree_fingerprint`; state persistence and receipts use `util.dump_json`. The fingerprint candidate changes path-byte treatment and JSON presentation while the router adds keyword evidence. Validate their existing suites together; parsed values and authority rules must remain intact.
- **Router ↔ receipt schema:** the router candidate touches `workflow_artifacts.py`, whose receipt registry is compared by the new schema tests. Its actual diff leaves that seven-kind registry unchanged; no textual collision or differing enum is introduced.
- **Fingerprint ↔ verifier/architecture:** `verification.py` consumes `changed_files`, `tree_fingerprint`, and stored-workflow validation; architecture fitness consumes the inspected repository state. The exact repaired utility must be present before the final combined gate and fresh receipts.
- **Installer ↔ all shipped source:** the payload carries managed workflow code and the schema. Preserve both template inputs for consumer-as-source reuse; installer inventory/rendering tests must run on the combined payload. Existing generated artifacts/releases remain separate.
- **Migration test ↔ packaged SQL:** its current-prefix fixture is checkout-derived and introduces no migration resource. Keep active #163/source 022 outside this batch; future integration requires separate assessment.
- **External receipt compatibility:** prior #162 review records a separate five-kind Trust CI validator limitation. All six inspected version-2 source specs currently cite only `verification`, `test_review`, or `code_review`; none adds a `data_review`/`bitrix_review` reference. Required route reviews still apply; coordinate the excluded validator successor before relying on new references in external validation.

No static source-import blocker was found. Prior passes remain predecessor evidence; the combined tree needs the route's complete verification and independent reviews, then exact-head external Trust CI.

Shared-memory fact for the coordinator: compare tree identities before replaying predecessor commits; here merged main and the reviewed predecessor are byte-identical, allowing 19 exact disjoint source imports while reconciling only shared handoffs.

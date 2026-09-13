# Independent F current-base transition ruling

Read-only architecture analysis for new route `a15f467e4575` in `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f2`. No repository edits, test execution, secret reads or external actions. Root owns the new change-package documentation and the route-selected `data_implementer` remains the sole product writer.

## Ruling

Re-extracting the eleven archived F product/test/config paths unchanged onto current E is a genuine transition to the updated predecessor, supported by actual Git ancestry. It does not require changing the archived route, code budgets, checker implementation or deployed policy. This is a scope/base ruling, not a passing verification or merge-eligibility claim.

Verified identities:

- Archived F: `517741da6e883c5feacbd2f029d745ffc5e2fec0`, whose merge parents are original F `3d72361...` and current E `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Current E: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`, whose parents are original E `356c7f991ee6835506255e823c06124068fc4e0e` and D review repair `bb93885034e52b80653efd96602fec182f7db10a`.
- `git merge-base --is-ancestor` confirms D repair is in current E and current E is in archived F. `git merge-base currentE archivedF` returns exactly current E.
- New F2 HEAD at inspection is exactly current E; only the new untracked change package exists. New route records that exact base. Archived route `5bc0f4cdffc5` still records original E `356c7f9...` and remains separate.

## Exact F delta

`git diff --name-only currentE archivedF`, excluding README/factory README/decisions and the archived engineering change package, contains exactly these eleven paths:

1. `architecture/rules.yaml`
2. `architecture/system.yaml`
3. `delivery/contracts/jsonschema/landing-publication-request.v1.schema.json`
4. `delivery/src/adaptive_delivery/landing_filesystem.py`
5. `delivery/src/adaptive_delivery/landing_publication.py`
6. `delivery/src/adaptive_delivery/landing_publication_contracts.py`
7. `factory/src/adaptive_factory/landing_publication_cli.py`
8. `factory/tests/__init__.py`
9. `factory/tests/test_landing_publication_cli.py`
10. `scripts/grok_landing_publish.py`
11. `tests/test_landing_architecture_boundaries.py`

There are no D repair files in this delta. Rules add only the publication CLI source to the offline boundary. The model adds only its offline ownership and publication-request schema ownership. Inventory adds only the publication CLI. The two architecture changes preserve all budget values and policies; parsed `code_budgets` at current E and archived F are identical.

## D repair is already base content

The following files are byte-identical at D repair, current E and archived F:

| Path | SHA256 |
| --- | --- |
| `factory/src/adaptive_factory/server.py` | `825e594624e35b4459cf66d35873eaf62c854391aba70ea31f94c7ec41dae358` |
| `factory/src/adaptive_factory/settings.py` | `0241a3e27200444bc3114da6e9c2940c6551d6db9e2112e74d6ab4c056c6dd02` |
| `factory/tests/test_landing_server.py` | `1a70c29bc8a5436017cb1b25d5b7ec2d780f90a15210af3249e5e1885dfcd671` |

Thus retaining current E automatically retains D's alias rejection and complete owned-resource cleanup. Do not copy earlier frozen versions over those files during F2 extraction.

## Meaning of the archived failure

`/tmp/agbp-sweep/split-f-inherited-change-fitness.json` records `fitness_status=fail`; its only failing/unsupported category is `background_job`, reason `queue_provenance_unresolved`, finding `unsupported changed-source background job semantics: factory/src/adaptive_factory/server.py`. `code_budget` is `pass` with no findings. The report compares an old-route scope that includes the later inherited D server repair. Moving to a genuinely advanced E predecessor makes this file inherited base content for F2; it does not establish that the scanner limitation is repaired or erase its old failure.

Preserve that report and archived route unchanged. Any outstanding verification/review obligation for the D/E repair remains upstream work. This ruling neither substitutes fresh evidence for those branches nor waives an external check.

## Source parity and new evidence conditions

Use archived F `517741d...`, not original frozen `f31406e`, as the eleven-path extraction source. Archived F includes the additional PublicationStore schema validation and its strengthened regression tests. In particular preserve exact column/STRICT/rowid/index/foreign-key/object validation, the literal `GLOB 'sqlite_*'` inventory filter, and the schema-lookalike plus committed-effect restart/restore tests. The archived writer report and `split-f-publication-frozen-deviation.patch.json` explain that deliberate frozen-source deviation.

After extraction require all eleven file bytes and executable modes to equal archived F and the three D repair files above to remain unchanged. Check the complete product delta against current E for extra/missing paths; let root update documentation against the actual new package. Obtain fresh prescribed verification and the five new-route reviews (code, test, security, release, data) bound to the new tree/base. Archived local receipts, old grants and any prior external check cannot be reused as new-route authority. No tagging, merge, publication or deployment follows from this source-only ruling.

Durable fact: current E already contains D repair and is archived F's actual merge-base; their product delta is exactly the eleven intended F paths. Re-extraction must preserve archived F's schema-validation correction while recording fresh current-base evidence, with the old unsupported queue finding left intact.

# Test review resume — K16 README + toolchain docs

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Reviewer: `test_reviewer` (read-only except this report). Route: `56da62035c35`. Write owner: `general_implementer`.  
Inspected tree: uncommitted docs/test delta vs HEAD `5915b56db7d6aedcd52a6c023418db84d45dd98f`. VERSION unchanged `2.0.11`.  
Scope: crashed K16 README + toolchain docs pass. Did **not** require live PostgreSQL or image build.

Did **not** re-record `grok_verify` (would rewrite the fingerprint-bound receipt). Independently re-ran the named focused tests, parsed the first README mermaid, and compared `toolchain.json` / doctor / bucket-B signals to the tests.

**PASS.**

| ID | Required case | Test / evidence | Result |
| --- | --- | --- | --- |
| P0 | First mermaid is K16; 16 IDs; `len(edge_lines)==C(16,2)=120` | `tests/test_structure.py::test_readme_stack_graph_is_complete` + independent parse | Covered, green |
| P0 | `docker`/`syft`/`trivy`/`cosign` exist and `required is False` | `tests/test_toolchain.py::test_real_toolchain_json_required_and_optional_sets` | Covered, green |
| P0 | Cosign has no `built` key and still does not fail doctor | Product `check_tool` + doctor on this host | OK (test does not require a built pin) |
| P0 | H1 remains `v2.0.11` | `test_version_identity_matches_readme` | Covered, green |
| P0 | New tools missing must not fail doctor | `test_optional_missing_does_not_fail_doctor` + live `run_doctor` | Covered, green |
| P0 | No root `docker-compose.yml` (bucket B / `trivy-config`) | filesystem + `test_this_repo_shaped_tree_omits_bucket_b` | Covered, green |
| P0 | `grok_verify --mode pr` PASS: unittest + coverage + ruff + bandit | `.grok-stack/runtime/receipts/56da62035c35/verification.json` | Recorded PASS; fingerprint matched this tree before this report |

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this docs slice | **PASS.** The K16 graph contract, optional scanner catalog, version identity, and doctor fail-open for optional tools are locked. |
| Characterization coverage | **PASS.** The graph test now derives 120 from `itertools.combinations` on 16 IDs instead of a literal `45`. Toolchain catalog presence + `required: false` is asserted. Surrounding no-GHA / no-root-packaging / bucket-B tests were not weakened. |
| Verification evidence | **PASS.** `grok_verify --mode pr` receipt `status=pass` on fingerprint `6dd8cec1905b527a620cc3a5bbb23ebcb6f916dfaa011436f86af8504024182c` (matched current tree at review start). Checks: unittest 166 OK, coverage 75% (`fail_under` 74), ruff, bandit. This report will stale that fingerprint; that is expected after a review write. |
| Residual test gaps | Documented below. None is a return-to-implementer item for this slice. |

Do not return this docs resume to an implementer for missing tests of the named K16 / optional-toolchain characterizations.

This report is local preflight. It is not the App-owned policy-epoch Check Run `adaptive-trust-ci/verified@<policy-sha12>`.

---

## 1. Diff under review vs `5915b56`

Product/test files dirty (not leftover change-package paperwork):

- `tests/test_structure.py` — rename `test_readme_local_stack_graph_is_complete_k10` → `test_readme_stack_graph_is_complete`; six Trust CI IDs appended; edge count is `len(list(itertools.combinations(nodes, 2)))` (120), not literal `45`.
- `tests/test_toolchain.py` — catalog must contain `docker`, `syft`, `trivy`, `cosign`, each `required is False`.
- `.grok-stack/config/toolchain.json` — grok `built`/`fallback` `1.0.5`; four optional tools appended.
- `README.md`, `QUICKSTART.md`, `trust-ci/README.md`, `decisions.md`, `mistakes.md`, `engineering/runbooks/trust-ci-rollout.md`.

No root `docker-compose.yml` / `Dockerfile` / `package.json` / `.github/workflows/` added. `VERSION` not bumped.

---

## 2. README first mermaid vs `test_readme_stack_graph_is_complete`

Hardcoded ordered IDs (16):

`Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes, TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp`

Contract:

1. Whole-README text contains `Left --- Right` or `Right --- Left` for every unordered pair.
2. First ` ```mermaid ` fence is parsed.
3. Lines matching `\S+ --- \S+` must equal `C(16,2)=120`.

Independent parse of current `README.md`:

| Probe | Value |
| --- | --- |
| Node count in test list | 16 |
| `C(16,2)` | 120 |
| Mermaid fences | 1 |
| `\S+ --- \S+` lines in first fence | **120** |
| Unique stripped edge lines | 120 |
| `-->` lines | 0 |
| Missing pairs | none |
| Unexpected mermaid `---` lines | none |
| Node-role table IDs | same 16 (not asserted by the test) |
| Caption still says Trust CI is outside the graph | no |

First fence edges run `Route --- Skills` … `Holdout --- GitHubApp` (README L79–L198 = 120 lines). Table `| --- |` rows sit **outside** the fence, so the mermaid-only count does not over-count markdown rules.

The first mermaid **does** satisfy the test. Focused unittest: **ok**.

Same residual as the old K10 lock: pairwise search is still whole-README, count is mermaid-only. A prose `Route --- Skills` could theoretically cover a missing mermaid pair if the fence still had 120 other edges. Unlikely on this README; not a fail.

---

## 3. Toolchain catalog vs `test_toolchain.py`

`test_real_toolchain_json_required_and_optional_sets` now also loops `('docker', 'syft', 'trivy', 'cosign')` and asserts `id in tools` and `required is False`. It does **not** assert `built` / `minimum` / `fallback` / `profile`.

Current `.grok-stack/config/toolchain.json` matches that contract:

| id | required | built | minimum | fallback | profile |
| --- | --- | --- | --- | --- | --- |
| docker | false | 29.7.2 | 24.0 | 29 | trust-ci |
| syft | false | 1.51.0 | 1.0 | 1.51 | supply-chain |
| trivy | false | 0.74.0 | 0.50 | 0.74 | supply-chain |
| cosign | false | **absent** | 2.0 | 2.4 | supply-chain |

No `grype`, no standalone `docker-compose` tool id, no required `psql`.

**Cosign with no `built` key is OK for the test** and for doctor:

- `check_tool` uses `str(spec.get('built') or '')`. Empty built skips the “older than built” branch (`if found and built and …`).
- Missing optional tool returns `status='info'`, not `fail`.
- This host: `cosign` is not installed → doctor `tool:cosign` is `info` (`not installed; optional for supply-chain; required>=2.0 if used (built ); … fallback Cosign 2.4`).
- Empty `(built )` in the info message is cosmetic, not a fail.

Focused unittest: **ok**.

---

## 4. Version identity

`VERSION` is `2.0.11`. README H1 is `# Adaptive Grok Build Pro v2.0.11`.  
`test_version_identity_matches_readme` asserts `readme.startswith(f"# Adaptive Grok Build Pro v{version}\n")`. Independently true. Unittest: **ok**.

Trust CI service identity **2.1.0** remains a separate sentence. No test collapses the two identities (pre-existing; not this slice).

---

## 5. Optional missing does not fail doctor

`test_optional_missing_does_not_fail_doctor` copies the tree (including the new catalog), runs `run_doctor`, and asserts no `tool:*` status `fail`. It still names `tool:php` as the example optional. `failures == []` is what would catch a new `required: true` scanner that is missing on the copy host.

Live `run_doctor` on this tree: php/composer/cosign = `info`; docker/syft/trivy = `pass` at the declared built pins; **no tool fails**.  
`test_project_doctor_has_no_failures` also **ok**.

New tools being `required: false` is why doctor stays green without cosign installed.

---

## 6. No root compose / bucket B

Root has no `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, `compose.yaml`, `Dockerfile`, or `package.json`. `.github/workflows/` does not exist.

`adaptive_grok.verification._trivy_config` emits `trivy-config` only when a root `Dockerfile`/`dockerfile`/`Containerfile` **or** `docker-compose*.yml`/`docker-compose*.yaml` exists. Trust CI compose files live under `trust-ci/` (`compose.yaml`, not `docker-compose.yaml`) and do not trip that glob.

`QualityContourTests.test_this_repo_shaped_tree_omits_bucket_b`: **ok** (`trivy-config` not in check names).  
`test_no_github_actions_workflow_exists`: **ok**.

---

## 7. `grok_verify --mode pr` recorded PASS

Receipt: `.grok-stack/runtime/receipts/56da62035c35/verification.json`

| Field | Value |
| --- | --- |
| status | pass |
| mode | pr |
| profiles | base |
| created_at | 2026-08-23T19:48:36+00:00 |
| tree_fingerprint | `6dd8cec1905b527a620cc3a5bbb23ebcb6f916dfaa011436f86af8504024182c` |
| match at review start | **yes** (same fingerprint) |

Checks in that receipt:

- git-diff-check pass
- secret-scan pass (0 potential secrets)
- contract-structure pass
- sql-safety pass
- **ruff** pass
- **bandit** pass
- **python-unittest** pass — `Ran 166 tests in 43.497s OK`
- **coverage** pass — TOTAL 75%, `fail_under` 74

`grok_verify` still discovers only root `tests/`, not `trust-ci/tests`. Pre-existing. Out of scope for this docs slice. Live Postgres / image build were **not** required here.

Writing this report changes the tree fingerprint; the verification receipt becomes stale after this file lands. Re-record after review writes if the controller needs a current receipt.

---

## 8. README Requirements table vs toolchain pins — residual, acceptable

There is **no** test that the README Requirements table matches `toolchain.json` built/minimum/fallback pins.

Historical: at HEAD `5915b56`, `test_real_toolchain_json_required_and_optional_sets` only locked `python3`/`git` required and `php`/`gh`/`node` optional. `git log -S 'Requirements' -- tests/` is empty. Graph tests never parsed the table. This gap is not new.

Manual check of the current table vs catalog (not test-locked):

| README row | Matches catalog? |
| --- | --- |
| Python 3.10 / 3.12.3 / 3.12 / yes | yes |
| Git 2.34 / 2.43.0 / 2.43 / yes | yes |
| Grok CLI 1.0.0 / 1.0.5 / 1.0.5 | yes |
| gh / Node / npm / PHP / Composer pins | yes (numeric) |
| Docker 24.0 / 29.7.2 / 29 / optional | yes |
| Syft 1.0 / 1.51.0 / 1.51 / optional | yes |
| Trivy 0.50 / 0.74.0 / 0.74 / optional | yes |
| Cosign 2.0 / — / 2.4 / optional | yes (`built` absent) |

Prose differences a table-sync test would have to special-case: Node minimum `18` vs catalog `18.0`; Node fallback `20 LTS` vs `20`; Required column is English (`for the TUI`, `optional`) not a boolean. The machine contract is `toolchain.json` + doctor. Acceptable residual for this slice; do not block.

---

## 9. Surrounding suite (not weakened)

| Test | Still adequate? |
| --- | --- |
| `test_version_identity_matches_readme` | Yes. H1 still v2.0.11. |
| `test_no_github_actions_workflow_exists` | Yes. |
| `test_trust_ci_control_plane_is_complete` | Yes. `trust-ci/compose.yaml` still required; not a root compose. |
| `test_root_has_no_packaging_marker` | Yes. |
| `test_optional_missing_is_info_not_fail` | Yes. Uses a synthetic php spec, not the new ids. |
| `test_this_repo_shaped_tree_omits_bucket_b` | Yes. Root still has no Dockerfile/compose/package.json. |
| `test_trivy_signal_without_binary_is_skip` | Yes. Fixture plants a root Dockerfile; unrelated to this slice. |
| Trust CI live class / restart drill | Not re-run; not required for this docs slice. Prior `test-review.md` on `2865fdc` remains the live-harness review. |

No test reintroduces `.github/workflows/` or a required scanner.

---

## 10. Gaps (not fail)

- **README Requirements table ↛ toolchain pins.** Historical; table currently matches; prose fields would need a dedicated parser. Acceptable residual.
- **No assert of `built`/`minimum`/`fallback`/`profile`** on docker/syft/trivy/cosign. Catalog drift of pins would not fail `test_real_toolchain_json_required_and_optional_sets`. Doctor would still fail-open if they stay optional.
- **Cosign missing `built` is not asserted.** Adding a fake built pin would still pass. Product-correct today.
- **Node-role table and “no `-->`”** are not asserted. Count + pairwise cover the load-bearing graph rule.
- **Pairwise still whole-README.** Count is mermaid-only (the K10 fix kept). Same residual as prior test review.
- **`test_optional_missing_does_not_fail_doctor` names php only.** `failures == []` still covers new optional tools.
- **`grok_verify --mode pr` does not discover `trust-ci/tests`.** Pre-existing. Operators keep the handoff unittest on `trust-ci/tests` for control-plane code. Not this docs slice.
- Leftover untracked `engineering/changes/20260817-user-query-вычисти-*` is in the verify `changed_files` list. Not a test gap; do not commit it as this work.

None of these would let the named resume regressions return unnoticed: K10/45 mermaid, required scanners, VERSION bump, doctor fail on missing cosign, or a root `docker-compose.yml` tripping `trivy-config`.

---

## Verdict (repeat)

**PASS.** Coverage for this docs/toolchain resume is adequate. Residual test gaps are historical or out of slice (README table vs pins; no live Postgres/image build).

Focused tests re-run here (all OK):

```text
tests.test_structure.StructureTests.test_readme_stack_graph_is_complete
tests.test_structure.StructureTests.test_version_identity_matches_readme
tests.test_structure.StructureTests.test_no_github_actions_workflow_exists
tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets
tests.test_toolchain.ToolchainTests.test_optional_missing_does_not_fail_doctor
tests.test_toolchain.ToolchainTests.test_optional_missing_is_info_not_fail
tests.test_verification_doctor.DoctorTests.test_project_doctor_has_no_failures
tests.test_verification_doctor.QualityContourTests.test_this_repo_shaped_tree_omits_bucket_b
```

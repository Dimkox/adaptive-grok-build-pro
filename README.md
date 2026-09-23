# Adaptive Grok Build Pro v2.0.19

MIT-licensed tooling for task-routed AI-assisted development, external verification and human-controlled delivery with **Grok Build**.

## Current state

Identity: **2.0.19 candidate**. The latest published release remains [`v2.0.18`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.18), published **2026-09-16T13:52:24Z** from the merged artifact-child commit `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`. Its tag, ZIP and sidecar are immutable. The `v2.0.19` ZIP and sidecar are not published until the separate artifact-child merge and exact release gates complete.

| Layer | Dated source and runtime observations |
| --- | --- |
| Repository source | `main` observed on September 22 at `130ce4a42d9f9bbd1b56772d40b19ae530283205` (PR #185); this candidate adds bounded repository-owned guards related to #35/#39 plus owned fixes for #73/#167 on `release/v2.0.19-factory-bugfixes`. #48 is excluded from this mixed tree by `FIT-TRUST-CI-SEPARATION` and remains linked through #186 with the external-owner portions of #35/#39 and all of #36; no broad issue closure is claimed. The fix tree is pending final verification and protected PR delivery. Published tag `v2.0.18` stays immutable at `e7d0f72`; M8/DEV work is excluded. |
| Installed L5 (September 19) | Primary Qwen is accepted at `f12807c2` / `qwen-omni-intl`; Grok stays accepted at `26a0d3d`. Both are **active and enabled**. Separate Omni remains at `e7d0f72`. |
| Proven runtime result (September 19) | Primary Qwen Omni produced `artifact_ready` in **4.991 s**, usage **766/195**; separate readback made zero POSTs. Grok previously completed in **26.947 s**. [Exact evidence and limits](engineering/runbooks/l5-primary-continuation-2026-09-19.md). |
| Remaining acceptance | A full external pilot with maintainer acceptance, a qualifying M8 cohort/activation, and general M9 operational qualification are **not established**. L5 artifact generation establishes no public-site publication. |

The `v2.0.19` candidate is the single release train for bounded local guards related to #35/#39 and owned fixes for #73/#167. Its durable [change package](engineering/changes/20260923-release-v2-0-19-with-fail-closed-factory-issue-f-4317e6/brief.md) keeps fix-tree verification, release metadata, artifact-child provenance and publication separate. #48 is reserved for a separate Trust CI-only change; #35/#36/#39/#48 remain linked to #186 for external-owner closure rather than receiving fabricated fixes. Final frozen-tree verification, current receipts and external delivery remain required before publication.

Source templates default to live execution off. The observed Qwen and Grok services use separately provisioned configurations with live execution explicitly enabled.

- Current source adds [`adaptive-landing-submit`](engineering/runbooks/l5-provider-failover.md): durable text/safe-DOCX submission through Qwen → Grok → OpenAI → Claude → OpenRouter, authenticated capability/attempt APIs, and atomic SQLite observations. Ambiguous submissions reconcile the same child; existing artifacts prevent further generation. Grok and primary Qwen now have accepted direct runtime results; the three added providers/full chain remain unqualified for inference. Monetary cost remains unknown; publication stays separate.
- Trust CI repository-scoped immutable profiles are implemented in code and documented by the example catalog; the worker uses `TRUST_CI_HOLDOUT_PATH` and `TRUST_CI_HOLDOUT_HOST_PATH` as independently configured trusted roots, validated binary-first before dependency construction. The capability is pending a separately reviewed and approved server-side policy/holdout installation; no deployed policy or branch protection is changed by it.

Start with [START_HERE.md](START_HERE.md) and [PROJECT_STATE.json](PROJECT_STATE.json). Runtime operation is described in the [L5 runbook](engineering/runbooks/l5-production-runtime.md); milestone acceptance remains in the [roadmap](DARK_FACTORY_ROADMAP.md). Delivery is PR-only: the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` check from GitHub App ID `4694114` must cover the exact PR head. Local receipts are preflight evidence. **No GitHub Actions:** this repository keeps deployed verification policy and holdout validation outside the PR-controlled tree, runs checks on the exact SHA, and binds the required result to its GitHub App identity.

## Optional Python test workers

The existing runner remains unchanged without opt-in. To select automatic workers, create `.grok-test-runner.json` containing `{"schema_version":1,"workers":"auto"}`; `GROK_TEST_WORKERS` overrides the requested value after the configuration file is validated. Accepted requests are `auto` or an integer from 0 through 64. Explicit integers are not quota-clamped, and `GROK_TEST_WORKERS=0` selects sequential execution.

On Linux, `auto` uses the minimum of 28, process affinity or CPU-count fallback, and finite CPU quotas visible through actual cgroup membership and mounts. Finite quotas use `max(1, quota // period)`; malformed, unreadable or ambiguous capacity conservatively selects one worker. This does not establish hidden ancestor limits, reserved CPU time or available PID/memory capacity.

Where this runner cannot provide its required parallel-process cleanup, a positive request selects the existing `unittest-degraded` engine before execution. Supported parallel execution retains its strict pins; measured serial execution retains pinned coverage. An actual failed parallel run is never retried serially. The implementation lives in `.grok-stack/adaptive_grok/python_test_runner.py` and its private `_cpu_capacity.py` helper; native Windows and older-interpreter qualification remain separate from fixture-based evidence.

## Delivery history

<details>
<summary>Published releases, source lineage and earlier evidence</summary>

- `v2.0.16`: PR #79 checked head `2b1517986b9b5b83a95b1286baac161074c58175`, App check `103797448701`, attestation `90cb34aa-6eb5-49ca-a0ec-104e11c5e722`; tag object `8486ddb648f97e79a5f3a81d9b539378d2d4b301` binds merge `969c4f65f54ef9230f3f94587e228098d1c2ecb9`. ZIP SHA-256 `71f63a1089f4009cc65ed0afb5b755418fa5a8bf1dd4ce2aebae2f1b8cc746d7`. Candidate wording inside the released archive is its historical build snapshot.
- L5 source landing: PR #75 merged the union of slices #65-#71 on `2026-09-13T17:35:51Z` as `eb9df64bca333f30ec58f8c725a021360e22ed92`, tree `1c8d72a50c0631c0222d111de1403ace4347aab2`, identical to attested final-slice head `e6a813e4c16543f262ced2d9ea353caaad9452d1`. Union head `ac7ae2def67a267c227ab5703843337d4bb6f4be` passed App check `103760385178`, attestation `e859743f-d0ed-48f0-a389-f5637e645c30`; #65 landed separately and the remaining slices closed by content. [Exact slice ledger](engineering/reviews/l5-delivery-stack.json) and [evidence policy](engineering/changes/20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b/evidence/README.md) preserve each check. PR #72 landed that evidence; PR #77 delivered contract-inventory, prohibited deploy-member and PDF-worker hardening. Installation and provider activation followed this source landing separately.
- `v2.0.15`: PR #27 checked head `9fcc9d943c74260c02a920a59490143f91cb38b2`, App check `101365945968`, merged as `fd51dcfed6b33f4a8707c0db602328146df17cc9`; published `2026-09-05T20:17:20Z`, ZIP SHA-256 `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`. GitGuardian was `SKIPPED` after the operator classified its public CSP digest finding as a false positive. The separate default-off [`pilot/`](pilot/) targets one pinned issue/repository through one Codex turn and separately granted branch/draft-PR transports. The [pilot handoff](engineering/runbooks/design-partner-pilot-v2.0.15.md) records the initial target drift and review repairs; it is not external maintainer acceptance.
- `v2.0.14`: PR #24 checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57`, App check `101099224099`, merged as `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`; published `2026-09-04T16:58:48Z`, ZIP SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`. This was the offline L5 19-member artifact epoch, retained alongside later 20/22-member epochs.
- `v2.0.13`: PR #22 delivered M1-M9 repository source, preserving migrations `001`-`018`. Checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9`, App check `100955508827`, attestation `74f1bbb2-3098-4d35-a42f-d49351d81c4a`, merged `2026-09-04T08:31:49Z` as `8599d45f4f28285381b05a53feb3059de92eb2a8`. Earlier M1-M3 stack and M4-M9 checkpoints remain in `PROJECT_STATE.json`.
- M0 Live Trust Authority and the PR #7/#6 runtime/policy-loop repairs are delivered. Independent [`trust-ci/`](trust-ci/) has service identity **2.1.0**, separate from the product version; it owns PostgreSQL jobs, isolated runners, external holdout checks and signed attestations. Deployed policy and credentials stay outside the PR trust domain.
- PR #12 delivered the approval CLI repair; PR #19 delivered the optional SEO side project. Open/unresolved work has a dated inventory in `PROJECT_STATE.json`; historical check success requires fresh base/head validation before merge.

</details>
## Read first

1. [START_HERE.md](START_HERE.md)
2. [PROJECT_STATE.json](PROJECT_STATE.json)
3. [AGENTS.md](AGENTS.md)
4. [decisions.md](decisions.md)
5. [mistakes.md](mistakes.md)
6. [DARK_FACTORY_ROADMAP.md](DARK_FACTORY_ROADMAP.md)
7. [CHANGELOG.md](CHANGELOG.md)
8. [QUICKSTART.md](QUICKSTART.md)
9. [`trust-ci/README.md`](trust-ci/README.md)
10. [`factory/README.md`](factory/README.md)
11. [delivered design-partner pilot package](engineering/changes/20260905-feature-implement-a-single-operator-codex-github-0ce2d6/brief.md)
12. `.grok-stack/runtime/active-route.json` if present (machine-local route; it may be absent in a clean clone and is not merge authority)
13. This README’s [map](#map) and [executable architecture](#executable-architecture)

## How work runs

Source-of-truth order is in AGENTS.md. Typed M1 intent is validated first, executable M2 architecture second, and target-owned M3 governance third; local receipts bind all configured layers to one worktree fingerprint but remain preflight evidence. Canonical governance JSON and exact handoffs outrank generated `decisions.md` / `mistakes.md` projections, while external Trust CI policy, holdout, signed approvals, and exact-SHA attestation remain the higher merge authority described in AGENTS.md. Large work is split into small subtasks that share `decisions.md` / `mistakes.md`. Local loop: route → change package → one write owner → if the product changed, `grok_verify --mode pr` and independent local reviews → `ready` → branch and pull request. The deployed Trust CI service verifies the exact PR SHA under server-side policy, executes an external holdout bundle before repository checks, rejects source mutation, checks signed human approval scopes, signs the attestation, and publishes `adaptive-trust-ci/verified@<policy-sha12>` through its GitHub App. A human owns merge, tag and production promotion.

For a fresh clone, bootstrap state comes from `START_HERE.md` / `PROJECT_STATE.json` first. Runtime route files are not expected to be committed; when no route exists, continue the explicitly named active PR/branch or route a new task before implementation.

## Map

- [START_HERE.md](START_HERE.md) — zero-context agent/human entrypoint
- [PROJECT_STATE.json](PROJECT_STATE.json) — machine-readable milestone handoff
- [AGENTS.md](AGENTS.md)
- [decisions.md](decisions.md)
- [mistakes.md](mistakes.md)
- [DARK_FACTORY_ROADMAP.md](DARK_FACTORY_ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)
- [QUICKSTART.md](QUICKSTART.md)
- [VERSION](VERSION)
- [`.grok/skills/`](.grok/skills/)
- [`.grok/agents/`](.grok/agents/)
- [`.grok/hooks/`](.grok/hooks/)
- [`scripts/grok_route.py`](scripts/grok_route.py)
- [`scripts/grok_change.py`](scripts/grok_change.py)
- [`scripts/grok_spec.py`](scripts/grok_spec.py)
- [`scripts/grok_artifacts.py`](scripts/grok_artifacts.py)
- [`schemas/change-spec.schema.json`](schemas/change-spec.schema.json)
- [workflow source schema](schemas/workflow-source-v1.schema.json)
- [workflow task graph schema](schemas/workflow-task-graph-v1.schema.json)
- [workflow convergence report schema](schemas/workflow-convergence-report-v1.schema.json)
- [architecture model](architecture/system.yaml)
- [architecture rules](architecture/rules.yaml)
- [architecture adoption marker](architecture/adoption.json)
- [architecture system schema](schemas/architecture-system.schema.json)
- [architecture rules schema](schemas/architecture-rules.schema.json)
- [architecture CLI](scripts/grok_architecture.py)
- [generated architecture views](architecture/generated/context.mmd)
- [governance rules](governance/rules/index.json)
- [governance debt](governance/debt/index.json)
- [canonical-example registry](governance/canonical-examples/index.json)
- [governance rule schema](schemas/governance-rule.schema.json)
- [debt schema](schemas/debt-entry.schema.json)
- [canonical-example schema](schemas/canonical-example.schema.json)
- [governance handoff schema](schemas/governance-handoff-v1.schema.json)
- [governance CLI](scripts/grok_governance.py)
- [`scripts/grok_verify.py`](scripts/grok_verify.py)
- [`scripts/grok_review.py`](scripts/grok_review.py)
- [`scripts/grok_approve.py`](scripts/grok_approve.py) — exact action/resource delegated local grant only
- [`scripts/grok_deploy.py`](scripts/grok_deploy.py)
- [`scripts/grok_doctor.py`](scripts/grok_doctor.py)
- [`scripts/grok_demo.py`](scripts/grok_demo.py)
- [local demo assets and fixtures](.grok-stack/demo/index.html)
- [local demo OpenAPI v1 contract](engineering/contracts/openapi/adaptive-demo.v1.json)
- [investor demo guide](docs/INVESTOR_DEMO.md)
- [`scripts/install_into.py`](scripts/install_into.py)
- [`trust-ci/`](trust-ci/) — external merge trust, deployed independently
- [`factory/`](factory/) — delivered M4-M8 control/evaluation source plus the L5 HTTP/media normalizer, dedicated SQLite/Unix host, deterministic artifacts and offline recovery; operational providers remain disabled by default
- [`delivery/`](delivery/) — delivered M9 staged-delivery/recovery source plus the explicit owner-controlled filesystem publication adapter and durable reconciliation; operational effects require exact authority
- [`pilot/`](pilot/) — published single-operator exact-issue/Codex/candidate/validation/draft-proposal vertical; disabled by default and without merge/deploy authority
- [`DARK_FACTORY_ROADMAP.md`](DARK_FACTORY_ROADMAP.md) — dependency-ordered M0-M9 program status and acceptance-relative schedule
- [`engineering/runbooks/`](engineering/runbooks/)
- [`packages/`](packages/)
- [`examples/bitrix-module/`](examples/bitrix-module/)
- [`.agents/skills/seo-landing/`](.agents/skills/seo-landing/) — optional Codex SEO landing skill
- [`side-projects/seo-landing-showcase/`](side-projects/seo-landing-showcase/) — non-indexable Russian showcase
- [LICENSE](LICENSE)

## What this is

- Zero-context project handoff through `START_HERE.md` and `PROJECT_STATE.json`
- Task routing + domain skills (Bitrix, API/events, data, frontend, security, incidents, …)
- Quality profiles and change packages under `engineering/changes/`
- Strict typed change intent with stable criterion/evidence IDs and deterministic spec fingerprints
- Strict executable architecture with deterministic digests, exact-state diff, drift, fitness, and projection-only diagrams
- Controlled governance with candidate-only agent input, reviewed lifecycle, exact evidence digests, canonical examples, and intentional-debt records
- Advisory model-neutral Spec Kit, BMAD, and Superpowers artifact imports with stable task graphs and deterministic convergence (never route, governance, approval, receipt, or merge authority)
- Separate durable local factory control with immutable handoffs, fenced PostgreSQL scheduling, bounded recovery and Unix-socket administration
- Integrated M5 execution, M6 validation, M7 shadow, and M8 autonomy boundaries under `factory/`, local-only M9 staged delivery under `delivery/`, and the L5 landing runtime with bounded artifact generation
- Separate operator-owned `pilot/` boundary with built-in default-off phased CLI, one exact repository/base, one Codex start, one test command, literal GitHub effect resources, deterministic restart recovery, and no automatic write retry
- Local verification / review receipts via `scripts/grok_*.py`
- Offline [historical evidence accounting](engineering/runbooks/historical-autonomy-evidence.md) via `scripts/grok_history.py` separates observed PRs, source-identified work units, acceptance, intervention coverage and exact-profile metadata; imported history has no M8 qualification or authority effect.
- [Cross-project confirmations](engineering/project-confirmations/README.md) index dated, source-pinned examples without adding M8 qualifying tasks or activation.
- Multi-agent discipline described in `AGENTS.md`
- One-command local browser tour backed by the same read-only route, spec, architecture and governance logic
- `AGENTS.md` starts with the self-learning rule and writes to `decisions.md` / `mistakes.md`
- Optional independently deployed Trust CI that removes merge trust from prompts, agents and local runtime
- GitHub App-owned policy-epoch Checks, external holdout validation and signed exact-SHA attestations

## Executable architecture

The M1 typed change spec remains business-intent and acceptance authority. The separate architecture authority is the canonical [system model](architecture/system.yaml) plus [fitness rules](architecture/rules.yaml), validated by the [system schema](schemas/architecture-system.schema.json) and [rules schema](schemas/architecture-rules.schema.json). This repository explicitly records adoption in [architecture/adoption.json](architecture/adoption.json). Generated Mermaid files under [`architecture/generated/`](architecture/generated/context.mmd) are sorted text projections only:

Declared repository paths are exclusive ownership boundaries. A more-specific nested path owns its subtree; equal-specificity ties are invalid. The shared `trust-ci/compose.yaml` configuration is owned once by the Trust CI worker node, while the Docker engine remains a separately modeled runtime node connected by the explicit Docker API deployment edge.

- [context](architecture/generated/context.mmd)
- [container](architecture/generated/container.mmd)
- [deployment](architecture/generated/deployment.mmd)
- [data flow](architecture/generated/data-flow.mmd)
- [trust boundary](architecture/generated/trust-boundary.mmd)

The [architecture CLI](scripts/grok_architecture.py) is dependency-free and bounded. `validate`, `summary`, and `drift` inspect the current target-owned model. `diagram` renders all five literal artifacts to stdout without mutating the repository; `diagram --check` performs a no-follow comparison against the checked-in projections. `diff` and `fitness` require an explicit base plus an exact 40-character head SHA or `--worktree`; exact inputs are read from Git objects and do not consult mutable route state. Worktree evidence is diagnostic and never claims an exact head SHA.

Architecture change growth is governed by six finite overlapping error rules. The original M2 rule remains unchanged over its exact six non-factory prefixes (`1,000,000` bytes / `10,820` lines / `5,000` AST); separate rules bound the seven-prefix aggregate and the `factory`, `factory/src`, `factory/contracts`, and `factory/tests` scopes. Every matching rule is enforced independently with complete path-segment matching, and unknown line metrics fail closed; minification and stacked-route partitioning are not budget substitutes.

```bash
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py summary --json
python3 scripts/grok_architecture.py drift --json
python3 scripts/grok_architecture.py diagram --json
python3 scripts/grok_architecture.py diagram --check --json
python3 scripts/grok_architecture.py diff --base <40-char-sha> --head <40-char-sha> --json
python3 scripts/grok_architecture.py fitness --base <40-char-sha> --head <40-char-sha> --pre-risk red --json
```

Diagram rendering is stdout-only and repository-read-only. To update a checked-in projection, apply the reviewed rendered text through the normal source-edit workflow and then run `diagram --check`; projections are never authority. Malformed, unknown, unsafe, excessive, partially missing, or applicable-but-unsupported adopted architecture fails closed. Installer-delivered examples live under [`.grok-stack/templates/architecture/`](.grok-stack/templates/architecture/system.example.yaml), but every plan and payload excludes the consumer-owned `architecture/system.yaml`, `architecture/rules.yaml`, and `architecture/adoption.json`; follow the manual review-and-adopt sequence in [QUICKSTART.md](QUICKSTART.md).

The M4 factory is modeled as an isolated local-preflight trust domain with only Unix HTTP and its own PostgreSQL edge. Installer payloads include its source, migrations, OpenAPI contract, locked dependency solution, mandatory disposable verification harness and placeholder-only local configuration, but never credentials, sockets, databases or runtime state. Installation does not run migrations, run verification or activate a service.

The queue and installer safety boundary is specified in the [approved pivot design](docs/superpowers/specs/2026-08-27-m2a-queue-installer-pivot-design.md) and its [implementation plan](docs/superpowers/plans/2026-08-27-m2a-queue-installer-pivot.md). Queue fitness and `new_queue` risk consume one bounded abstract-interpreter result: relevant uncertainty fails closed, while unrelated common method names remain non-queue.

## Controlled governance

The canonical M3 authority is the three target-owned JSON registries under [`governance/`](governance/rules/index.json), validated against the four closed governance schemas. Registry content, repository text, agent notes, reviewer names, and `actor_kind` values are untrusted claims until the required independent external authority binds the exact record and digest. Agents can create candidates only; expired, deprecated, revoked, conflicted, stale, or unsupported records do not become effective.

Validation runs after typed-spec and architecture validation. A configured governance failure prevents any local verification or review receipt from being recorded. Successful local receipt cores include `governance_contract_version`, `governance_digest`, and a domain-separated `governance_evidence_digest` bound to current rule/debt/example/schema state, M2 architecture digest, applicable Git commits, and the worktree fingerprint. These local bindings are not the exact committed `GovernanceHandoffV1` and are never merge authority.

```bash
python3 scripts/grok_governance.py validate --json
python3 scripts/grok_governance.py summary --json
python3 scripts/grok_governance.py check-projections
python3 scripts/grok_governance.py handoff --base <40-char-sha> --head <40-char-sha> --architecture-evidence <path> --json
```

`project` prints proposed non-authoritative `decisions.md` and `mistakes.md` content without writing; `check-projections` compares those views without mutation. Exact handoff publication additionally requires a clean exact Git state, independently rederived M2 evidence, matching base/head SHAs, and zero governance findings.

## Requirements

Pins are **minimum or newer**. `built` is the version this local stack was verified on. If a tool is missing or older than minimum, `python3 scripts/grok_doctor.py` prints an **install offer** for the fallback (or install a newer version).

| Tool | Minimum | Built | Fallback | Required |
| --- | --- | --- | --- | --- |
| Python 3 | 3.10 | 3.12.3 | 3.12 | yes |
| Git | 2.34 | 2.43.0 | 2.43 | yes |
| Grok Build CLI | 1.0.0 | 1.0.5 | 1.0.5 | for the TUI |
| GitHub CLI (`gh`) | 2.40 | 2.86.0 | 2.86 | for human-owned GitHub Release |
| Node.js | 18 | 24.19.0 | 20 LTS | frontend profiles |
| npm | 9 | 11.17.0 | 10 | frontend profiles |
| PHP | 8.1 | 8.2 | 8.2 | PHP/Bitrix profiles |
| Composer | 2.2 | 2.7 | 2.7 | PHP/Bitrix profiles |
| Docker Engine | 24.0 | 29.7.2 | 29 | Trust CI host (optional) |
| Syft | 1.0 | 1.51.0 | 1.51 | supply-chain SBOM (optional) |
| Trivy | 0.50 | 0.74.0 | 0.74 | supply-chain vuln scan (optional) |
| Cosign | 2.0 | — | 2.4 | supply-chain sign/verify (optional) |

```bash
python3 scripts/grok_doctor.py --offer-install
```

Machine-readable local pins: `.grok-stack/config/toolchain.json` (its `workflow_sources` block pins the advisory workflow-document parsers). Trust CI uses separately built API, worker and runner images pinned by immutable SHA-256 digest in deployment and server policy.

### Workflow sources (advisory parsers — not installed by this stack)

| Component | Pinned | Upstream | Observed latest | Observed |
| --- | --- | --- | --- | --- |
| Superpowers | 6.3.0 | obra/superpowers | 6.3.0 | 2026-09-15 |
| BMAD Method | 6.12.0 | bmad-code-org/BMAD-METHOD | 6.12.0 | 2026-09-15 |
| GitHub Spec Kit | 1.0.7 | github/spec-kit | 1.0.7 | 2026-09-15 |

These rows are dated currency observations for the workflow artifact adapters, not install targets; `tests/test_workflow_sources.py` keeps them bound to `.grok-stack/config/toolchain.json` and to named parser tests. Accepted document shapes and the known-unparsed list are defined in the [upstream format amendment](docs/superpowers/specs/2026-09-15-workflow-artifact-adapters-upstream-amendment.md).

## Install into a project

Existing repositories are read-only installer inputs. Generate a deterministic manifest and dependency advice, then apply an update through a normal reviewed source-change commit:

```bash
python3 scripts/install_into.py --plan /path/to/your/repo
```

The historical positional form and `--dry-run` are planning aliases. `--force` is rejected; dependency advice is output only and no dependency runner is executed.

To create a complete installation, the target must be absent:

```bash
python3 scripts/install_into.py --materialize-new /path/to/new/repo
```

This materialization mode is supported only on Linux with descriptor-relative `O_NOFOLLOW`/`O_DIRECTORY` operations and both libc and the target filesystem supporting `renameat2(RENAME_NOREPLACE)`. If any required capability is unavailable or the filesystem rejects it, materialization exits nonzero and fails closed without publishing the target; there is no fallback to replace, merge, or in-place copying. Use `--plan` plus a normal reviewed source-change for an existing consumer or for a platform/filesystem without those capabilities.

Materialization builds and verifies one owned sibling stage and publishes it with fail-closed no-replace semantics. If constructor identity becomes unresolved, it preserves the entry for manual inspection and reports `manual cleanup required: installer ownership is unresolved`; it never deletes an unproven replacement. It refuses an existing, symlink, or special-file target. The payload includes:

```text
.grok/            → project .grok/          (config, hooks, agents, skills)
.agents/skills/   → project .agents/skills/
.grok-stack/      → project .grok-stack/
scripts/          → project scripts/
AGENTS.md         → project AGENTS.md
decisions.md      → project decisions.md
mistakes.md       → project mistakes.md
engineering/      → project engineering/  (if empty scaffold needed)
```

It includes the governance engine, CLI, four closed schemas, and explicitly non-authoritative change-package templates. It excludes `trust-ci/`, `.github/workflows/`, `architecture/adoption.json`, `architecture/system.yaml`, `architecture/rules.yaml`, and every target-owned `governance/**/index.json` registry. The installer never creates or overwrites a target governance registry. Adopt architecture and governance manually only after reviewing target truth as described in [QUICKSTART.md](QUICKSTART.md).

Then in the project:

```bash
cd /path/to/your/repo
grok inspect    # should see skills + AGENTS.md
grok            # start TUI
```

Invoke the main controller skill:

```text
/adaptive-delivery
```

or just describe a development task — Grok should pick up skills from `.grok/skills/`.

The independent `trust-ci/` service is deployed once as infrastructure; it is not copied into every consumer unless that repository will use the same external check protocol.

## Scripts

Local loop: route → change → verify → independent reviews → `ready` → pull request. `scripts/grok_deploy.py` is prepare-only and must not bypass protected-branch or exact-SHA requirements.

Declared route `human_gates` require a separate decision in the active change package. The package stores the initial gate declaration and a digest; a missing or changed declaration in the active route or route snapshot fails closed. Inspect gate status with `python3 scripts/grok_gate.py status`; record only an explicit operator decision with `python3 scripts/grok_gate.py decide <gate> <approved|rejected> --reason "..." --actor "..."` (production decisions also require `--action`; approve the migration plan with `--action migration-plan`; external-write decisions require exact `--action external-write --resource ...`). Decisions are bound to the active route, change, gate and scope digest. They are mutable local workflow evidence, not authenticated human identity, delegated grants, Trust CI signed approvals or merge authority. Production and external-write operations still require their exact delegated grants.

| Script | Role |
|--------|------|
| `scripts/grok_route.py` | Classify / show route |
| `scripts/grok_change.py` | Start durable local change package |
| `scripts/grok_governance.py` | Validate/summarize target-owned governance, check read-only projections, and emit an exact clean-state handoff |
| `scripts/grok_status.py` | Local runtime status |
| `scripts/grok_gate.py` | Inspect or record route-bound local human-gate decisions |
| `scripts/grok_verify.py` | Local verification preflight (unittest, Ruff, Bandit, measured coverage in `pr`/`release`) |
| `scripts/grok_review.py` | Record local review receipt |
| `scripts/grok_approve.py` | Delegated local action/resource grant bound to repository, route, change, exact HEAD and tree fingerprint; not accepted by Trust CI |
| `scripts/grok_deploy.py` | Prepare-only human last mile |
| `scripts/grok_doctor.py` | Local health check |
| `scripts/grok_demo.py` | Start the loopback-only read-only product tour using bundled sample and checkout-derived evidence |
| `scripts/install_into.py` | Plan an existing repository read-only or atomically materialize an absent new target |
| `adaptive-trust-ci` | External API, worker, migration, signed approvals, holdout verification, attestation verification and app-bound branch protection |

## Local browser demo

```bash
python3 scripts/grok_demo.py --open
```

The command binds only `127.0.0.1`, prints `http://127.0.0.1:8765/`, and needs no frontend build, package installation, database, credential or Git query. The tour computes route and typed-spec previews in memory, reads architecture and governance summaries from this checkout, and shows bundled sample verification evidence. Nothing is written and nothing leaves the host. Press `Ctrl-C` to stop.

Browser assets are same-origin only under `default-src 'self'`, render text through `textContent`, and use system font stacks, so the page works offline. See [docs/INVESTOR_DEMO.md](docs/INVESTOR_DEMO.md) for the five-minute walkthrough, expected states and port troubleshooting.

## Hooks

Lifecycle adapters live in `.grok/hooks/` and are registered in both:

- `.grok/hooks.json` — doctor/structure contract (`command` + `commandWindows`)
- `.grok/hooks/adaptive.json` — Grok project-hook discovery

Trust the folder once (`/hooks-trust` or `grok --trust`). Hooks classify prompts and enforce local policy (secrets, Bitrix core, destructive commands, control-plane mutations, and exact delegated side-effect grants). Hook failure remains fail-open to avoid locking an interactive agent; this is why hooks are not merge authority. External Trust CI remains fail-closed for the App-owned required Check Run.

## Package

```bash
python3 scripts/package_stack.py
```

Creates `dist/adaptive-grok-build-pro-v<VERSION>.zip` and its checksum sidecar. See the [release package and operator guide](packages/README.md) for published artifacts and packaging requirements.

## Bitrix

See skills under `.grok/skills/bitrix-development/` and example module in `examples/bitrix-module/`.

## License

[MIT License](LICENSE).

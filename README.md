# Adaptive Grok Build Pro v2.0.13

A commercial-grade product for **Grok Build** — free of charge, public, and MIT-licensed.

## Current state

- Fresh-agent bootstrap: start with [`START_HERE.md`](START_HERE.md), then [`PROJECT_STATE.json`](PROJECT_STATE.json). A clean clone must be sufficient to understand the current milestone without chat history.
- Identity: **2.0.13** (`VERSION`, README H1). Exact shipped-package parity determines whether `packages/adaptive-grok-build-pro-v2.0.13.zip` represents the current source HEAD: after a tracked mutation, rebuild the artifact-only child only if parity fails. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or release is claimed.
- Standing contract: [AGENTS.md](AGENTS.md) — first section is agent self-learning into [decisions.md](decisions.md) / [mistakes.md](mistakes.md); delivery is PR-only and merge trust comes from the App-owned policy-epoch check `adaptive-trust-ci/verified@<policy-sha12>` on the exact pull-request SHA.
- Local quality gate: `python3 scripts/grok_verify.py --mode pr` plus route-selected reviews. These are preflight evidence, not merge authority.
- Independent Trust CI: [`trust-ci/`](trust-ci/) — self-hosted API/worker, PostgreSQL durable jobs, Ed25519 approvals and attestations, external holdout validation, isolated no-network runner containers, GitHub App Checks API and app-bound branch protection. **No GitHub Actions.**
- M0 Live Trust Authority is delivered on `main`. PR #7 repaired the Trust CI workspace/runtime path, PR #6 fixed target-aware shell policy/denial loops, and PR #5 delivered the milestone.
- Trust CI service identity is **2.1.0** (`trust-ci/pyproject.toml`); it is not product `2.0.13`. The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; the required App-owned check remains `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114`, with deployed policy digest `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`.
- M1 is implemented and reviewed in the accepted stack, but only its early typed-spec slice and design/plan reached `main` through PRs #4 and #8. The full M1/M2 head passed the current-epoch gate and PR #10 merged it only into `milestone/m1-typed-intent-evidence`, so M1 delivery remains partial and M2 is not delivered to `main`.
- M3 is implemented and reviewed; PR #11 merged it into `milestone/m2-executable-architecture`, not `main`. The accepted M2+M3 aggregate is `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` and still needs one current-main delivery path.
- The local integration now contains the complete M4-M9 source chain: M4 durable control, M5 bounded execution, M6 semantic validation, M7 shadow handoff, M8 earned-autonomy evaluation, and M9 deterministic preview/staging/bounded-canary plus least-authority recovery. Migrations `001`-`018` are preserved; execution and delivery remain disabled by default and no operational provider, credential, persistence, systemd, network, merge, or production capability is introduced.
- PRs #12 and #13 remain stale old-epoch `ACTION_REQUIRED` work: their unique lazy CLI import/tests and repository-scoped Trust CI profiles, respectively, are absent from `main` and require clean successor extraction. PR #15's current-epoch `adaptive-trust-ci/verified@06ecf1c875bc` conclusion is `FAILURE` while GitGuardian is `SUCCESS`; the failure cause was not inspected or inferred. Its wholesale M1-M3 aggregate is superseded, while investor-demo commit `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique and also require clean successor extraction. No successor PR for #12, #13, or #15 is claimed.
- Exact local source checkpoints are M4 `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` → M5 `85cd4343143915ce9342634e7fe81886b6394871` → M6 `c6d48ffd8594b3baab1a575021452ea5dfa2a98b` → M7 `00e0e4f9a6f50844bf9e0ffc7139d3283dda889f` → corrected M8 `a937ac8d200a4e143c295fabd482b19bc8cc4286`; M9 implementation code checkpoint `64b10689ce78a0464a494440f3fa981e18789687` is combined with that corrected predecessor in the current candidate tree. PR #22 is open for the current M9 integration branch; it is not merged or delivered.
- Local source completion is distinct from acceptance. M8 still lacks a factual cohort of at least 30 human-accepted tasks and activation; M9 still lacks real signed input, an operational environment, exercised recovery proof, and production authority. Artifact rebuild, exact-head verification, five independent reviews, App-owned Trust CI, protected merge, tag, and release remain separate gates.
- Do not add `pyproject.toml` / `requirements.txt` / `setup.py` at repository root (flips repo detect). `trust-ci/pyproject.toml` is intentionally scoped to the independent service.
- Optional SEO side project: PR #19 delivered it to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; [`.agents/skills/seo-landing/`](.agents/skills/seo-landing/) provides repository-scoped `$seo-landing` generation/audit/fix modes, while [`side-projects/seo-landing-showcase/`](side-projects/seo-landing-showcase/) is its Russian static showcase and stays non-indexable until a production origin is supplied. This is delivered non-milestone work, not M0-M9 progress.

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
11. [active M9 change package](engineering/changes/20260904-m9-staged-delivery-on-exact-m8-f53275d-331ca7/README.md)
12. `.grok-stack/runtime/active-route.json` if present (machine-local route; it may be absent in a clean clone and is not merge authority)
13. This README’s stack graph and map

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
- [`schemas/change-spec.schema.json`](schemas/change-spec.schema.json)
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
- [`scripts/install_into.py`](scripts/install_into.py)
- [`trust-ci/`](trust-ci/) — external merge trust, deployed independently
- [`factory/`](factory/) — local M4 task control plane; no execution or merge authority
- [`delivery/`](delivery/) — local M9 staged-delivery/recovery package; sealed in-memory environment only and no production authority
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
- Separate durable local factory control with immutable handoffs, fenced PostgreSQL scheduling, bounded recovery and Unix-socket administration
- Integrated M5 execution, M6 validation, M7 shadow, and M8 autonomy boundaries under `factory/`, plus local-only M9 staged delivery under `delivery/`
- Local verification / review receipts via `scripts/grok_*.py`
- Multi-agent discipline described in `AGENTS.md`
- `AGENTS.md` starts with the self-learning rule and writes to `decisions.md` / `mistakes.md`
- Optional independently deployed Trust CI that removes merge trust from prompts, agents and local runtime
- GitHub App-owned policy-epoch Checks, external holdout validation and signed exact-SHA attestations

## Stack graph

Decorative inventory graph (K22): every listed core node is linked to every other with one of 231 `---` edges. It is an inventory regression only, not architecture authority or architectural evidence. The directed, trust-aware authority is the reviewed model and rules described below; prompts, generated views, local receipts, and delegated grants are not merge authority.

```mermaid
graph TD
  Contract["AGENTS.md"]
  Decisions["decisions.md"]
  Mistakes["mistakes.md"]
  TrustAPI["trust-ci API"]
  TrustWorker["trust-ci worker"]
  Postgres["PostgreSQL 17"]
  Runner["isolated runner"]
  Holdout["external holdout"]
  GitHubApp["GitHub App Checks"]
  Factory["local factory control"]
  M5Execution["M5 isolated execution"]
  M6Semantic["M6 semantic validation"]
  M7Shadow["M7 shadow PR bundle"]
  M8Autonomy["M8 trust profile"]
  M9Delivery["M9 preview/canary/recovery"]
  Route --- Skills
  Route --- Agents
  Route --- Hooks
  Route --- Policy
  Route --- Verify
  Route --- Packages
  Route --- Contract
  Route --- Decisions
  Route --- Mistakes
  Route --- TrustAPI
  Route --- TrustWorker
  Route --- Postgres
  Route --- Runner
  Route --- Holdout
  Route --- GitHubApp
  Skills --- Agents
  Skills --- Hooks
  Skills --- Policy
  Skills --- Verify
  Skills --- Packages
  Skills --- Contract
  Skills --- Decisions
  Skills --- Mistakes
  Skills --- TrustAPI
  Skills --- TrustWorker
  Skills --- Postgres
  Skills --- Runner
  Skills --- Holdout
  Skills --- GitHubApp
  Agents --- Hooks
  Agents --- Policy
  Agents --- Verify
  Agents --- Packages
  Agents --- Contract
  Agents --- Decisions
  Agents --- Mistakes
  Agents --- TrustAPI
  Agents --- TrustWorker
  Agents --- Postgres
  Agents --- Runner
  Agents --- Holdout
  Agents --- GitHubApp
  Hooks --- Policy
  Hooks --- Verify
  Hooks --- Packages
  Hooks --- Contract
  Hooks --- Decisions
  Hooks --- Mistakes
  Hooks --- TrustAPI
  Hooks --- TrustWorker
  Hooks --- Postgres
  Hooks --- Runner
  Hooks --- Holdout
  Hooks --- GitHubApp
  Policy --- Verify
  Policy --- Packages
  Policy --- Contract
  Policy --- Decisions
  Policy --- Mistakes
  Policy --- TrustAPI
  Policy --- TrustWorker
  Policy --- Postgres
  Policy --- Runner
  Policy --- Holdout
  Policy --- GitHubApp
  Verify --- Packages
  Verify --- Contract
  Verify --- Decisions
  Verify --- Mistakes
  Verify --- TrustAPI
  Verify --- TrustWorker
  Verify --- Postgres
  Verify --- Runner
  Verify --- Holdout
  Verify --- GitHubApp
  Packages --- Contract
  Packages --- Decisions
  Packages --- Mistakes
  Packages --- TrustAPI
  Packages --- TrustWorker
  Packages --- Postgres
  Packages --- Runner
  Packages --- Holdout
  Packages --- GitHubApp
  Contract --- Decisions
  Contract --- Mistakes
  Contract --- TrustAPI
  Contract --- TrustWorker
  Contract --- Postgres
  Contract --- Runner
  Contract --- Holdout
  Contract --- GitHubApp
  Decisions --- Mistakes
  Decisions --- TrustAPI
  Decisions --- TrustWorker
  Decisions --- Postgres
  Decisions --- Runner
  Decisions --- Holdout
  Decisions --- GitHubApp
  Mistakes --- TrustAPI
  Mistakes --- TrustWorker
  Mistakes --- Postgres
  Mistakes --- Runner
  Mistakes --- Holdout
  Mistakes --- GitHubApp
  TrustAPI --- TrustWorker
  TrustAPI --- Postgres
  TrustAPI --- Runner
  TrustAPI --- Holdout
  TrustAPI --- GitHubApp
  TrustWorker --- Postgres
  TrustWorker --- Runner
  TrustWorker --- Holdout
  TrustWorker --- GitHubApp
  Postgres --- Runner
  Postgres --- Holdout
  Postgres --- GitHubApp
  Runner --- Holdout
  Runner --- GitHubApp
  Holdout --- GitHubApp
  Route --- Factory
  Skills --- Factory
  Agents --- Factory
  Hooks --- Factory
  Policy --- Factory
  Verify --- Factory
  Packages --- Factory
  Contract --- Factory
  Decisions --- Factory
  Mistakes --- Factory
  TrustAPI --- Factory
  TrustWorker --- Factory
  Postgres --- Factory
  Runner --- Factory
  Holdout --- Factory
  GitHubApp --- Factory
  Route --- M5Execution
  Route --- M6Semantic
  Route --- M7Shadow
  Route --- M8Autonomy
  Route --- M9Delivery
  Skills --- M5Execution
  Skills --- M6Semantic
  Skills --- M7Shadow
  Skills --- M8Autonomy
  Skills --- M9Delivery
  Agents --- M5Execution
  Agents --- M6Semantic
  Agents --- M7Shadow
  Agents --- M8Autonomy
  Agents --- M9Delivery
  Hooks --- M5Execution
  Hooks --- M6Semantic
  Hooks --- M7Shadow
  Hooks --- M8Autonomy
  Hooks --- M9Delivery
  Policy --- M5Execution
  Policy --- M6Semantic
  Policy --- M7Shadow
  Policy --- M8Autonomy
  Policy --- M9Delivery
  Verify --- M5Execution
  Verify --- M6Semantic
  Verify --- M7Shadow
  Verify --- M8Autonomy
  Verify --- M9Delivery
  Packages --- M5Execution
  Packages --- M6Semantic
  Packages --- M7Shadow
  Packages --- M8Autonomy
  Packages --- M9Delivery
  Contract --- M5Execution
  Contract --- M6Semantic
  Contract --- M7Shadow
  Contract --- M8Autonomy
  Contract --- M9Delivery
  Decisions --- M5Execution
  Decisions --- M6Semantic
  Decisions --- M7Shadow
  Decisions --- M8Autonomy
  Decisions --- M9Delivery
  Mistakes --- M5Execution
  Mistakes --- M6Semantic
  Mistakes --- M7Shadow
  Mistakes --- M8Autonomy
  Mistakes --- M9Delivery
  TrustAPI --- M5Execution
  TrustAPI --- M6Semantic
  TrustAPI --- M7Shadow
  TrustAPI --- M8Autonomy
  TrustAPI --- M9Delivery
  TrustWorker --- M5Execution
  TrustWorker --- M6Semantic
  TrustWorker --- M7Shadow
  TrustWorker --- M8Autonomy
  TrustWorker --- M9Delivery
  Postgres --- M5Execution
  Postgres --- M6Semantic
  Postgres --- M7Shadow
  Postgres --- M8Autonomy
  Postgres --- M9Delivery
  Runner --- M5Execution
  Runner --- M6Semantic
  Runner --- M7Shadow
  Runner --- M8Autonomy
  Runner --- M9Delivery
  Holdout --- M5Execution
  Holdout --- M6Semantic
  Holdout --- M7Shadow
  Holdout --- M8Autonomy
  Holdout --- M9Delivery
  GitHubApp --- M5Execution
  GitHubApp --- M6Semantic
  GitHubApp --- M7Shadow
  GitHubApp --- M8Autonomy
  GitHubApp --- M9Delivery
  Factory --- M5Execution
  Factory --- M6Semantic
  Factory --- M7Shadow
  Factory --- M8Autonomy
  Factory --- M9Delivery
  M5Execution --- M6Semantic
  M5Execution --- M7Shadow
  M5Execution --- M8Autonomy
  M5Execution --- M9Delivery
  M6Semantic --- M7Shadow
  M6Semantic --- M8Autonomy
  M6Semantic --- M9Delivery
  M7Shadow --- M8Autonomy
  M7Shadow --- M9Delivery
  M8Autonomy --- M9Delivery
```

| Node | Role |
| --- | --- |
| Route | `scripts/grok_route.py` / active-route |
| Skills | `.grok/skills/` and `.agents/skills/` |
| Agents | `.grok/agents/` |
| Hooks | `.grok/hooks/` |
| Policy | `.grok-stack/adaptive_grok/policy.py` |
| Verify | `scripts/grok_verify.py` + typed-spec validation + criterion-bound local receipts |
| Packages | `packages/` + `scripts/package_stack.py` + durable `engineering/changes/**/change-spec.yaml` |
| Contract | `AGENTS.md` first rule: log to `decisions.md` / `mistakes.md` |
| Decisions | root `decisions.md` |
| Mistakes | root `mistakes.md` |
| TrustAPI | `trust-ci/` FastAPI image; HMAC webhook intake; no GitHub App key |
| TrustWorker | `trust-ci/` worker; claims PostgreSQL leases; publishes the Check Run |
| Postgres | Durable PostgreSQL 17 (`TRUST_CI_POSTGRES_IMAGE`); jobs, leases, approvals, attestations |
| Runner | Isolated no-network runner container; `policy.sandbox.image` must equal `TRUST_CI_RUNNER_IMAGE` |
| Holdout | External digest-pinned bundle, outside the PR checkout |
| GitHubApp | App-owned Checks `adaptive-trust-ci/verified@<policy-sha12>` bound to the App ID |
| Factory | Integrated local M4 control API/store under `factory/`; no external write, deployment or merge authority |
| M5Execution | Integrated bounded execution packet/result, offline adapter, broker and workspace boundary; disabled by default and no live provider capability |
| M6Semantic | Integrated independent semantic verdict, artifact validation and bounded-repair boundary; cannot self-approve implementation |
| M7Shadow | Integrated deterministic shadow bundle/outcome/cohort boundary; human merge remains mandatory |
| M8Autonomy | Integrated earned-autonomy profile/recommendation boundary over actual M7 records; no factual cohort or activation and authority is capped at L2 |
| M9Delivery | Integrated immutable staged-delivery/recovery source over actual M8 records; sealed local environment only, with no signed real input, operational adapter or production authority |

oneshots `migrate` / `runner-loader` reuse API/worker images; privileged rootless DinD is an execution edge of Runner.

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

Machine-readable local pins: `.grok-stack/config/toolchain.json`. Trust CI uses separately built API, worker and runner images pinned by immutable SHA-256 digest in deployment and server policy.

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

| Script | Role |
|--------|------|
| `scripts/grok_route.py` | Classify / show route |
| `scripts/grok_change.py` | Start durable local change package |
| `scripts/grok_governance.py` | Validate/summarize target-owned governance, check read-only projections, and emit an exact clean-state handoff |
| `scripts/grok_status.py` | Local runtime status |
| `scripts/grok_verify.py` | Local verification preflight (unittest, Ruff, Bandit, measured coverage in `pr`/`release`) |
| `scripts/grok_review.py` | Record local review receipt |
| `scripts/grok_approve.py` | Delegated local action/resource grant bound to repository, route, change, exact HEAD and tree fingerprint; not accepted by Trust CI |
| `scripts/grok_deploy.py` | Prepare-only human last mile |
| `scripts/grok_doctor.py` | Local health check |
| `scripts/install_into.py` | Plan an existing repository read-only or atomically materialize an absent new target |
| `adaptive-trust-ci` | External API, worker, migration, signed approvals, holdout verification, attestation verification and app-bound branch protection |

## Hooks

Lifecycle adapters live in `.grok/hooks/` and are registered in both:

- `.grok/hooks.json` — doctor/structure contract (`command` + `commandWindows`)
- `.grok/hooks/adaptive.json` — Grok project-hook discovery

Trust the folder once (`/hooks-trust` or `grok --trust`). Hooks classify prompts and enforce local policy (secrets, Bitrix core, destructive commands, control-plane mutations, and exact delegated side-effect grants). Hook failure remains fail-open to avoid locking an interactive agent; this is why hooks are not merge authority. External Trust CI remains fail-closed for the App-owned required Check Run.

## Package

```bash
python3 scripts/package_stack.py
```

Default output is `dist/adaptive-grok-build-pro-v<VERSION>.zip` (gitignored scratch). Tracked copies live in `packages/`; their presence alone does not claim a tag or GitHub Release, and `packages/README.md` records publication status. Production release packaging requires a clean repository root and derives its complete regular-file inventory, bytes and canonical `0644`/`0755` member modes from filtered exact Git `HEAD`; ignored and untracked filesystem files or ambient non-executable permission bits are not candidates. The tracked `2.0.13` candidate is tested independently against that tree's member names, blob bytes, modes, hashes and embedded manifest, so either ambient extras or a stale/substituted same-version ZIP with a regenerated sidecar fails. Generic manifest generation and `write_archive` remain compatible with non-Git filesystem targets. Zip members use the prefix `adaptive-grok-build-pro/`; packaging excludes symlinks/non-regular sources, binds no-follow source and output-parent descriptors through verified publication, streams with bounded memory, preserves umask/existing output and sidecar permissions, atomically publishes the ZIP and checksum from separate exclusive held fds, and never mutates a source manifest. Missing output parents are no-follow-bound, set and verified at exact mode `0700` independently of ambient umask; existing parents must be effective-UID-owned and private, and every canonical ancestor must exclude untrusted ownership/rename authority, with normal root-owned sticky `/tmp` semantics supported. Secure packaging fails with a controlled error when that boundary or descriptor-relative POSIX capabilities are unavailable, while explicit manifest generation and verification remain importable and compatible without those flags.

## Bitrix

See skills under `.grok/skills/bitrix-development/` and example module in `examples/bitrix-module/`.

## License

**MIT.** A commercial product that is free of charge: use, copy, modify, and ship it. The repository is public. No EULA, no paid tier. Local checks: `make doctor` / `make verify` / `make trust-ci-test`. Merge trust, when deployed, is the App-owned policy-epoch exact-SHA check described in [`trust-ci/README.md`](trust-ci/README.md).

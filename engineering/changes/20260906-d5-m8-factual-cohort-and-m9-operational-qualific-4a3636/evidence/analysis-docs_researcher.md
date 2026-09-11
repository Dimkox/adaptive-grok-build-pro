# Docs researcher — D5 M8 factual cohort / M9 operational qualification

Route: `4a3636699111`. Change: `20260906-d5-m8-factual-cohort-and-m9-operational-qualific-4a3636`.
Read-only sources: `git show` from `origin/main` (`fd51dcfed6b33f4a8707c0db602328146df17cc9`) and `origin/docs/v2.0.15-published-handoff` (`ef7c8faeb5d339c5b4343de61162ea611c130c4d`). Local checkout is stale `7c61e3b` / `VERSION` `2.0.12`.

No APIs were invented. Typed authority for M8/M9 remains the origin change-specs; Markdown cannot override them.

## What this working tree is (contradiction if used as D5 base)

| Fact | Local checkout | `origin/main` | `origin/docs/v2.0.15-published-handoff` |
| --- | --- | --- | --- |
| HEAD | `7c61e3b647924e5667d171d8b286e5d79b8a4efe` | `fd51dcfed6b33f4a8707c0db602328146df17cc9` | docs successor of published 2.0.15 |
| `VERSION` | `2.0.12` | `2.0.15` | `2.0.15` |
| `START_HERE.md` | absent | present (still calls 2.0.15 unpublished / latest pub `v2.0.14`) | present (2.0.15 **published** PR #27) |
| `PROJECT_STATE.json` | absent | present (`latest_published_release` `v2.0.14`, `observed_main_sha` `1751b585…`) | present (`latest_published_release` `v2.0.15`, `observed_main_sha` `fd51dcf…`) |
| `factory/` M8 autonomy | absent | present (`factory/src/adaptive_factory/autonomy.py`, `m7_autonomy_bridge.py`) | same lineage |
| `delivery/` M9 | absent | present (`delivery/src/adaptive_delivery/`, **no** `delivery/README.md`) | same |
| M8/M9 change packages | absent | present under `engineering/changes/20260904-m8-earned-autonomy-on-exact-m7-00e0e4f-3ec8b3/` and `…/20260904-m9-staged-delivery-on-exact-m8-f53275d-331ca7/` | same |

**Do not use this 2.0.12 checkout as the D5 implementation base.** It predates M4–M9 source, PR #22/`v2.0.13`, PR #24/`v2.0.14`, and PR #27/`v2.0.15`. Implementing cohort/activation here would fabricate a parallel product.

**Preferred continuation base:** published `origin/main` at `fd51dcf` (route `base_commit` already records this SHA). Reconcile docs using the **handoff** narrative for publication identity; `origin/main` `START_HERE.md` / `PROJECT_STATE.json` / `README.md` still describe 2.0.15 as unpublished and `v2.0.14` as latest tag — that is documentation lag on `origin/main` vs `origin/docs/v2.0.15-published-handoff`.

Active-route `base_fingerprint` `bd4efe5e70fcf9e9bf52829cb2f6ba62e7e32731bbcdd4a8e1832e4634b1a8fd` is bound to `fd51dcf`, not to local `7c61e3b`.

## Claimed vs forbidden (repository product vs operations)

### Already claimed (repository source only)

From `PROJECT_STATE.json` milestones (same M8/M9 notes on both origin refs):

- **M0–M9 implemented and delivered to `main` as repository product** via PR #22 merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9`, check `adaptive-trust-ci/verified@06ecf1c875bc` (check run `100955508827`, attestation `74f1bbb2-3098-4d35-a42f-d49351d81c4a`).
- **M8 source checkpoint** `a937ac8d200a4e143c295fabd482b19bc8cc4286` (`repair/m8-contract-boundary-20260904`): earned-autonomy contracts, actual-M7 bridge, one-level **L2-capped recommendation**, deterministic **L0 demotion**. Evidence package: `engineering/changes/20260904-m8-earned-autonomy-on-exact-m7-00e0e4f-3ec8b3`.
- **M9 source checkpoint** `64b10689ce78a0464a494440f3fa981e18789687` over exact M8: closed delivery records, actual-M8 bridge, one-step preview/staging/bounded-canary evaluation, sealed **in-memory** adapter, digest chain, least-authority recovery. Evidence package: `engineering/changes/20260904-m9-staged-delivery-on-exact-m8-f53275d-331ca7`.
- Trust CI success on PR #22 **establishes merge eligibility only** — not M8 autonomy or M9 operations (`milestones.M8.external_gate.notes`, `milestones.M9.external_gate.notes`).
- `factory/README.md` (origin): M4–M8 delivered in `v2.0.13`; “does not authorize deployment, live-provider action, persistent database mutation, M8 activation, or production acceptance.”
- `delivery/` has Python package + tests; **no** `delivery/README.md` on origin.

Handoff-only publication facts (not on stale local tree; **not** fully reflected in `origin/main` START_HERE):

- Tag **`v2.0.15`**, ZIP SHA-256 `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`, tag target `fd51dcf…`, PR #27 checked head `9fcc9d943c74260c02a920a59490143f91cb38b2`, check run `101365945968`, attestation `4a13e71c-25e7-4272-80fa-8153590edc84`. GitGuardian `SKIPPED` (operator false-positive on CSP fixture).
- Handoff `published_release.notes`: capability only; **no** real model attempt, target mutation, deployment, **M8 cohort/activation**, or **operational M9 qualification**.

### Forbidden to claim (explicit)

M8 `change-spec.yaml` `forbidden_outcomes`:

- FORBID-001: duplicate M7 producer/authority; caller-supplied M7 acceptance/currentness.
- FORBID-002: automatic activation; promotion above one level or L2; executable recommendation/demotion; provider/network/credential/command/delivery/production effect.
- FORBID-003: treating **synthetic fixtures** or source-only recommendations as a **real accepted cohort**, **current activation**, **M9 eligibility**, or production authority.

M9 `change-spec.yaml` `forbidden_outcomes`:

- FORBID-001: duplicate M8/M7 producers; caller-supplied eligibility/currentness/acceptance; opaque digest pairs as authority.
- FORBID-002: stage skipping; automatic final-canary or production; operational adapter; I/O; persistence; provider; external action.
- FORBID-003: recovery that widens exposure, restores unbound artifact, uses stale authority, or records duplicate/reordered evidence.

M8/M9 briefs: out of scope for real cohort acquisition, durable currentness, activation, persistence, network, credentials, production. M8 `state.json` remains `verifying` (source checkpoint language). M9 `state.json` is `ready` for **source checkpoint / dual-clone artifact**, not operational qualification.

D5 brief title: fail-closed activation; **no fabricated tasks**, **no production grant**, **no merge**.

`START_HERE.md` (both origin refs, milestone handoff item 5): do not describe M8 as active until exact-profile factual cohort **and** activation record exist; do not describe M9 as operational until signed inputs, environment, **exercised recovery**, and **human production authority** exist.

## Exact exit / activation criteria

### M8 — activation (factual cohort + independent gate)

Roadmap `DARK_FACTORY_ROADMAP.md` M8 (handoff/main ~L915; local 2.0.12 file has **no** “Current status” line):

**Trust-profile tuple (any material change starts a new cohort):** repository, change_class, agent_profile, validator_profile, model versions, prompt/definition digests, policy digest, runner image digest, holdout digest.

**Suggested levels:** L0 propose; L1 implement + human every PR; L2 automated reviewers + **human merges every PR**; L3/L4 auto-merge — **not initially available**; M8 source **caps at L2**.

**Minimum promotion conditions (roadmap):** configured minimum sample for the exact tuple; first-pass acceptance threshold; no critical security miss; no unauthorized protected-path/secret access; duplicate dispatch rate **zero**; rollback and escaped-defect below policy; validator false-negative below policy; human review time materially reduced; **production observability** for affected behavior.

**Immediate demotion → L0/L1:** production incident, security miss, incorrect auto-merge, rollback, policy bypass, unexplained metric regression, invalid attestation.

**Never initially eligible classes:** authz, PII/tenant, payments, migrations/destructive data, secrets, side-effect integrations, production deploy, Trust CI/governance/holdout/branch protection, destructive ops.

**Roadmap M8 exit criteria:** durable auditable trust profiles; promotion from empirical data not a toggle; policy changes invalidate old profiles; only approved green classes can auto-merge; demotion immediate; sampled human audit continues. *(Source delivery does not satisfy these; they remain operational.)*

**Typed M8 eligibility (AC-004 / requirements — activation gate, fail-closed):**

- ≥ **30 real accepted tasks** (`active_delivery.schedule.m8_calendar.minimum_human_accepted_tasks`: 30; calendar status **`indeterminate`**).
- ≥ **20% accepted audit sampling on every represented UTC day**.
- **Zero** safety / authorization / duplicate / demotion facts.
- Bounded quality, cost, latency, time, receipts, replay.
- Recommendation: **at most one level** above current, **never above L2**; `separate_activation_required=true`; `external_action_authorized=false`.
- Fail-closed on expired tuples, replayed cohorts, stale task facts, halted profiles, **missing M7 acceptance/currentness**, blocked M7 bundles.
- Synthetic fixtures = algorithm evidence **only**; cannot satisfy factual acceptance/currentness or activation.

### M9 — operational qualification (not source checkpoint)

Roadmap M9 (~L1011 origin): real signed input, operational environment/provider deployment, **exercised** recovery, production authority **absent**; production promotion **human-owned**.

**Roadmap exit criteria:**

- preview and staging reproducible from **exact SHA**;
- production artifacts **signed and verified**;
- canary has explicit success and abort criteria;
- **rollback is exercised**, not merely documented;
- no agent bypass of human promotion for non-approved classes;
- production outcomes update the empirical trust profile.

**`active_delivery.schedule.m9_entry_requires`:** `accepted_m8`, `signed_artifact`, `environment_evidence`, `recovery_evidence`.

**Typed M9 ACs (source already aims at these locally; ops still missing):**

- Closed records bind artifact/authority/repo/env/exposure/policy/holdout/runner/time/digest-chain; reject malformed/stale/duplicate/contradictory input.
- M8 seam recomputes producer digests; durable acceptance/currentness **remain false**.
- **Exactly one** authorized step preview → staging → bounded canary; **final canary and production** return `needs_human`; production **unreachable** to adapter.
- Only **sealed in-memory fake adapter**; at-most-once; chain ≤ 128.
- Recovery: halt, one-step lower exposure, or restore **exact prior signed artifact** only.
- Empty prior evidence is the only locally trusted start; nonempty prior needs a future trusted witness.

M9 work items in the roadmap remain **unchecked** (preview envs, signed supply-chain bind, canary cohorts, business metrics, automatic halt, recording outcomes). Treat them as **not done operationally**.

## Named blockers

1. **No factual 30-task cohort** for any exact trust-profile tuple; M8 calendar **indeterminate**.
2. **Durable currentness / M7 acceptance lookup unavailable** — M8 evaluation fail-closed; M9 advancement denied in source-only integration.
3. **No activation record** — recommendations non-operative; authority capped L2 conceptually but not activated.
4. **M9: no real signed environment/provider deployment**, no exercised recovery proof, no human production authority; production structurally unreachable.
5. **Synthetic tests cannot be reused as cohort evidence** (M8 FORBID-003).
6. **Do not fabricate tasks** (D5 title / M8 privacy: digest/id/metric/timestamp only).
7. **No production grant / no merge** for D5; local receipts ≠ Trust CI.
8. **Landing/pilot is a separate track:** handoff next_action is refresh landing policy for `80d6215` before one model attempt; that is **not** M8/M9 qualification (`current_unreleased_change` is `null` on handoff).
9. **Open PRs #12/#13/#15** stale/failing — unique scopes absent from main; not M8/M9 blockers but must not be claimed delivered.
10. **Using 2.0.12 local tree** as write base: missing `factory/`, `delivery/`, M8/M9 packages, `START_HERE.md`, `PROJECT_STATE.json`.

## Internal origin contradictions (docs, not APIs)

- `origin/main` `VERSION`/`README` H1 = `2.0.15`, but `START_HERE.md` / `PROJECT_STATE.json` still say unpublished 2.0.15 and latest published **`v2.0.14`** / `observed_main_sha` `1751b585…`. Handoff branch and `git rev-parse origin/main` = `fd51dcf` + published **v2.0.15**. D5 should treat **handoff + `fd51dcf`** as publication truth and treat main-tree START_HERE/PROJECT_STATE as **stale relative to the tag**.
- `delivered_milestones_on_main` includes M8/M9 while the same file says cohort/activation/ops **absent**. “Delivered” = **source on main**, not earned autonomy or staged delivery ops.
- M8 change `state.json` still `verifying`; M9 `ready` predates PR #22 merge — package states are **historical local checkpoints**, not current operational status.
- Local `DARK_FACTORY_ROADMAP.md` M8/M9 sections lack the origin “Current status” paragraphs; local roadmap is 2.0.12-era.

## D5 continuation implication (facts only)

Continue from **`origin/main` `fd51dcf` / published 2.0.15**, not this checkout. Keep activation **fail-closed**. Do not invent HTTP/CLI surfaces beyond existing `factory` / `delivery` modules named in the M8/M9 change-specs (`factory/tests/test_autonomy.py`, `delivery/tests/test_*.py`). Do not claim M8 active or M9 operational until the named evidence exists. Do not merge, grant production, or fabricate 30 tasks.

Sources: `START_HERE.md`, `PROJECT_STATE.json`, `DARK_FACTORY_ROADMAP.md` M8/M9, `factory/README.md`, M8/M9 `brief.md`/`requirements.md`/`release.md`/`state.json`/`change-spec.yaml`, `decisions.md` (2026-09-03 predecessor T0 / M8 cohort duration), `mistakes.md` (M8 routing `fix` substring; M9 stacked `base_commit`).

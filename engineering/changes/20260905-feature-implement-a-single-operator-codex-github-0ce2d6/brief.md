# Single-operator Codex/GitHub design-partner pilot

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260905-feature-implement-a-single-operator-codex-github-0ce2d6`
Base: `6f3b6ed2853b7a6f78804888cffca578d4dc9448` / tree `913f646649f878e97959d7ba2489a57de2379a1d`
Route: `0ce2d62a018e`
Risk: red after architecture expansion (`yellow -> red`)

## Problem and outcome

The released product proves a bounded offline landing vertical but does not change a separate repository or create a real pull request. This change adds one operator-owned, disabled-by-default pilot that can snapshot one issue from `Dimkox/ai-dark-factory-landing`, invoke one pinned Codex CLI in a proven sandbox, seal and validate one exact candidate, and—under two exact delegated grants—upload one non-force branch and create one draft PR.

The first live issue is a genuine stale-public-state defect: the landing still presents `v2.0.12` while product release `v2.0.14` is published. The accepted change must also use the honest product label `Governed Agentic Software Factory — Offline Technical Preview`. The live run may prove proposal creation; it cannot claim merge eligibility until the landing repository actually has the required App-owned exact-SHA Trust CI profile and protection.

## Scope

In scope: one repository/base epoch, one issue, one model, one invocation, one private clone, one configured unittest command, deterministic semantic checks, private SQLite replay state, two exact publication effects, observation-only reconciliation, and a factual human-outcome observer.

Out of scope: generic multi-repository orchestration, concurrency, automatic repair/retry, Claude/provider selection, issue mutation by the pilot, force push, merge/close/deploy, Trust CI administration, M8 cohort activation, M9 production authority, hosting and SEO deployment.

## Constraints

- The first target base is exactly `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
- The honest version/status issue may touch only `.htaccess`, `index.html`, `zh-cn/index.html`, `ko/index.html`, `nl/index.html`, `lv/index.html`, `km/index.html`, and `tests/test_landing.py`, all mode `100644`.
- `index.css` is protected at Git blob `4117a5f263d3500af4d397d3eac07f0d7b89b167`, SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`.
- Ubuntu `bubblewrap 0.9.0` plus the scoped AppArmor profile is the supported local sandbox prerequisite. A private clone alone is not process isolation.
- No credentials, `.env`, Codex auth files or GitHub token bytes are read or persisted by product code.

Canonical governance JSON under `governance/` remains separately reviewed authority. This package records intent; exact verifier output is the architecture/governance evidence.

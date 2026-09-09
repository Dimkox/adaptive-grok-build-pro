# Documentation and specification audit — M3 through M9

**Role:** `docs_researcher` (read-only analysis; this report is the only write)
**Audit basis:** repository-local documents and the active change package only; no web, live-system, credential, or secret inspection.
**Audit snapshot:** 2026-08-28. “Release” below means a separate PR-only milestone release, not a local source claim or a merge-authority claim.

## Authority and delivery rule

`DARK_FACTORY_ROADMAP.md` is the program backlog. It defines a strict chain: M1 + M2 + M3 feed M4, then M5, M6, M7, M8, and M9 ([lines 191-206](../../../DARK_FACTORY_ROADMAP.md#L191-L206)). Its continuation instruction requires one next-uncompleted milestone on a named branch, a milestone spec and plan, exact evidence, and a merged/proven predecessor before proceeding ([lines 1208-1215](../../../DARK_FACTORY_ROADMAP.md#L1208-L1215)). Therefore an umbrella M3–M9 package cannot serve as the release specification for any individual milestone.

The active route (`35568941ae59`) is high-risk AI/security work and selects `ai_implementer` as its sole writer. The current package is still `draft` ([state.json](../state.json)) and its typed authority has no acceptance criteria, invariants, forbidden outcomes, contracts, observability, approval scopes, or concrete success metric ([change-spec.yaml](../change-spec.yaml#L2-L30)). Its Markdown brief, requirements, architecture, test plan, release plan, and rollback plan are templates. It is unsuitable as an M3 release package until populated and narrowed to M3 alone.

## Findings

### F1 — Binding-spec provenance is broken (P0; blocks M3 and M4 scope/release)

Both detailed plans declare the same canonical design as their `Spec`:

- M3 plan [line 11](../../../docs/superpowers/plans/2026-08-28-m3-controlled-knowledge-debt.md#L11)
- M4 plan [line 11](../../../docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md#L11)

`docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` does not exist in this tree. The same absent file is called the “canonical design” in the older design package’s architecture document. The roadmap describes objectives and gates, but it does not replace the missing binding design: it does not give a versioned canonical source for the M3/M4 handoff definitions, nor a provenance record that binds an implementation plan to the exact design revision.

**Required correction before M3 implementation/release:** restore the canonical design at the cited path or deliberately replace all references through a reviewed, versioned superseding design. The replacement must record: document ID/version; source commit/tree fingerprint; relationship to the roadmap sections; M1 spec digest/version; M2 architecture handoff digest/version; M3 `GovernanceHandoffV1` version/digest; explicit M4 consumer compatibility; and the supersession decision. A link alone is insufficient—the design provenance must be immutable/fingerprint-bound in the M3 package.

### F2 — M3/M4 plans target a stale package; the active M3–M9 package is unbound and empty (P0 for M3/M4)

The M3 plan’s final-evidence task names `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/...` ([lines 543-585](../../../docs/superpowers/plans/2026-08-28-m3-controlled-knowledge-debt.md#L543-L585)); the M4 plan repeats that obsolete path for its PostgreSQL and review evidence ([lines 653-698](../../../docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md#L653-L698)). The active route instead names `engineering/changes/20260826-m3-m9-production-delivery-continuation-355689/`. No binding document explains whether the older package is superseded, whether its design gate is valid for the present route, or which exact M3/M4 head/fingerprint each evidence set will bind.

**Required correction before separate releases:**

- Create or complete one durable **M3-only** package with non-placeholder typed ACs, invariants, forbidden outcomes, governance schemas/contracts, exact predecessor identities, test evidence plan, rollback, release boundary, and the four required review-report destinations.
- Create a separate **M4-only** package only after M3’s merged/external prerequisite is recorded; bind its intake to the final M3 handoff and identify its disposable PostgreSQL exit evidence, migration recovery, schema ownership, and no-execution boundary.
- Update M3/M4 plans to the selected current package paths and remove the conflicting old-path instructions, preserving the historical design package as history rather than as the evidence destination.

### F3 — README and roadmap status surfaces are incomplete for an M3 candidate (P1; required before an M3 PR/release)

The living README current state lists M1 and M2-A only ([README lines 10-11](../../../README.md#L10-L11)) and its map does not include the M3 governance authority, governance schemas/CLI, or the M3-to-M4 handoff ([README lines 31-63](../../../README.md#L31-L63)). At the audit snapshot, M3 source files are present but uncommitted (`governance/`, governance schema files, and `tests/test_governance.py`); README must not claim them as reviewed/released yet. Once M3’s source and evidence exist, the README must add a conservative M3 current-state entry, map/authority ordering and commands, distinguish local evidence from external Trust CI, and state M4 is pending.

The roadmap’s M3 work items and exit criteria remain unchecked ([lines 455-539](../../../DARK_FACTORY_ROADMAP.md#L455-L539)), which is correct until source-backed evidence exists. Update only the M3 items actually proven; do not mark M4–M9 progress from an M3 release. The M3 plan itself mandates this README/roadmap update and requires M4 to remain pending ([lines 516-520](../../../docs/superpowers/plans/2026-08-28-m3-controlled-knowledge-debt.md#L516-L520)).

## Missing documentation/specification artifacts by release

| Milestone | Existing authoritative material | Required before its separate release |
| --- | --- | --- |
| M3 | Roadmap section; detailed plan, but it points to a missing canonical design | Restored/superseding binding design with provenance; M3-only change package; closed governance/handoff contract references; completed README/roadmap status; final fingerprint-bound verification and selected review evidence. |
| M4 | Roadmap section; detailed plan, also pointing to missing design and obsolete package path | M4-only package after M3 is actually accepted; pinned M3 handoff/base; factory schema/API/event/role/migration contract provenance; PostgreSQL exit/recovery plan and evidence destinations; README/roadmap update after proof. |
| M5 | Roadmap section only | M5 binding spec and implementation plan; immutable packet, workspace/isolation, secret-broker, network-policy, artifact/retention, and run-manifest schemas; explicit M4 compatibility fingerprint; isolated-runtime and recovery test/rollback/release package. |
| M6 | Roadmap section only | M6 binding spec and plan; versioned finding/verdict/coverage schemas; independent-validator provenance and M5/M4 input bindings; bounded-repair/escalation policy; exact-SHA evidence and reviewer-separation tests. |
| M7 | Roadmap section only | M7 binding spec and plan; PR-summary, delegated-operation and shadow-cohort schemas; authority boundary documenting that local grants never replace Trust CI/human merge; WIP/age/cost controls and shadow-report criteria. |
| M8 | Roadmap section only | M8 binding spec and plan; durable trust-profile/cohort/promotion/demotion schemas and thresholds; binding to M7 evidence and deployed-policy provenance; explicit human/security approval gates, audit, immediate-demotion, and rollback plan. |
| M9 | Roadmap section only | M9 binding spec and plan; preview/artifact/canary/promotion/rollback contracts; exact merged-SHA and signed-manifest provenance; measurable abort criteria, recovery drill evidence, and strict human-promotion boundary for ineligible classes. |

No individual M5–M9 spec or implementation-plan artifact exists under `docs/superpowers/specs/` or `docs/superpowers/plans/`; roadmap text alone is intentionally insufficient under the per-milestone continuation rule.

## Recommended documentation release sequence

1. Repair binding design provenance and split/complete the current M3 package before writing an M3 completion claim.
2. Deliver M3 only; update README and only source-proven M3 roadmap entries with its exact final fingerprint/evidence status.
3. After the M3 predecessor gate, create M4’s dedicated package and correct its plan references; repeat the same process one milestone at a time for M5–M9.

This report does not assert any milestone has merged, passed external Trust CI, been deployed, or received human approval.

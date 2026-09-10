# AI evidence accounting analysis

Route: `78b680187560`. Role: `ai_architect`, read-only application analysis. Scope: historical delivery accounting, without changing controller levels or external authority.

## Findings

`factory/src/adaptive_factory/autonomy.py` permits `L0`, `L1`, and `L2`; its tuple accepts only `low_risk_text_only`, with ceiling `L2`. A substantial historical code task remains real delivery evidence even when outside that task class. A GitHub merge is evidence of delivery through a branch, not evidence of a unique product task, human acceptance, or an operator intervention.

The current M7 ready-for-PR bundle has only `blocked_pending_durable_lookup`. `M7AutonomyBridgeV1.external_acceptance_available` and `.currentness_available` both return false. Consequently an offline historical accounting result cannot activate an M8 profile even when a caller supplies all its metadata. Do not alter these producer facts or mint replacement receipts.

M8 additionally binds each task/run/exact SHA to unique M7 bundles and outcomes, receipt digests, audit facts, quality, failure counters, cost and latency. M7 evaluation requires at least 30 accepted tasks, 14 observation days or a completed release cycle, 30 baseline review samples, quality/budget/safety thresholds and containment evidence. M8 requires at least 30 accepted tasks for the exact tuple, a minimum 20% audit rate and audit coverage on each represented day. Historical merged PR totals cannot be subtracted from 30 as if all shared one tuple.

## Minimal input semantics

- Inventory identity: explicit project ID; unique observation ID; source reference/digest; observed timestamp; artifact kind (`pull_request`, `commit`, or `task`); task ID nullable; delivery kind including `product_change`, `branch_sync`, and `unknown`; exact result SHA nullable. Source strings are untrusted data and are never commands or instructions.
- Merge fact: explicit observed merge state and timestamp. Author/merger actor type is descriptive only. Deduplicate observations by project and source identity; count unique explicit task IDs separately. A branch sync stays in delivery inventory and does not create another product task. An ancestor commit or stacked PR needs explicit relationship evidence before being treated as delivered.
- Acceptance: `accepted`, `rejected`, or `unknown`, with an explicit evidence reference required for either observed decision. A merge event alone does not satisfy acceptance. An offline cited acceptance is a historical observation; it is not a verified external security approval or M7 receipt.
- Intervention coverage: `complete`, `partial`, or `unknown`, with nullable nonnegative observed intervention count and a source reference for any measured count. `complete` means a defined task/session window with evidenced start/end and event coverage; Git history alone cannot support that claim. `partial` counts are lower bounds. `unknown` cannot contain an invented zero. Count operator decisions, corrective instructions, manual fixes, and recoveries only when explicitly attributable; do not infer them from a GitHub `User` actor.
- Outcome measurements: nullable repair count, rollback count, escaped-defect count, cost and latency with measurement provenance where available. Missing source evidence remains null. A title containing a repair or rollback word is insufficient to establish an outcome measurement.
- Qualification coverage: task class nullable; partial tuple fields nullable; optional explicitly evidenced exact tuple. Preserve code-heavy tasks with task class `other` or their recorded unsupported class. Report their delivery and acceptance while excluding them from the currently supported class count.

The required exact tuple fields are `schema_version`, `repository_id`, `task_class`, `m7_change_class`, `m7_cohort_key_digest`, `provider_mapping_digest`, `agent_digest`, `validator_digest`, `provider_digest`, `model_digest`, `prompt_digest`, `policy_digest`, `runner_digest`, `holdout_digest`, `authority_digest`, `authority_ceiling`, and `expires_at`. Reuse the existing tuple parser to validate a claimed M8-compatible tuple. Never reconstruct unknown historical revisions from current repository defaults. Incomplete metadata can be retained without constructing a tuple or inventing its digest.

## Output counters and diagnostics

Report `projects_observed`, `merged_prs_observed`, `branch_sync_prs_observed`, `unique_product_tasks_identified`, and `task_identity_unknown_observations` independently. Keep accepted, rejected, and acceptance-unknown task counts separate. Source observations without task identity cannot become accepted unique tasks automatically.

Report complete-session task count, partial-session task count, unknown-session task count, observed intervention total/lower bound, and intervention count over completely measured sessions. Any intervention average or zero-intervention proportion must use only complete sessions and print its denominator. When that denominator is zero, the rate is null, not zero. The observed lower bound may be zero only when explicitly measured evidence records zero; when there are no measured records the total is unknown.

Report task-class-supported, task-class-unsupported, task-class-unknown, exact-tuple-complete and exact-tuple-incomplete coverage independently. For each incomplete record list sorted `missing_profile_fields`; for a supplied but incompatible profile report a distinct unsupported/invalid reason. List cohort groups only by a complete valid exact tuple digest, never by project or model name alone. Historical acceptance plus complete tuple is still only a candidate evidence count, not a qualified M8 acceptance. Keep any reported `qualification_status` fixed to an evidence-only state with explicit blockers.

Useful ordered blockers are `task_identity_missing`, `acceptance_evidence_missing`, `intervention_coverage_incomplete`, `task_class_unknown` or `task_class_unsupported`, `exact_profile_missing_fields`, `m7_bundle_missing`, `m7_outcome_missing`, `external_acceptance_unavailable`, `currentness_unavailable`, `audit_coverage_missing`, and `quality_cost_latency_outcomes_unknown`. Return all material gaps rather than only the first one; missing metadata and unsupported class must not erase observed work.

## Ordered next capabilities

1. Finish the evidence inventory and task/PR relationship mapping; attach any recoverable explicit acceptance and intervention observations with their provenance. This fixes undercounting without claiming missing facts.
2. Instrument future executions with stable task/run identity, exact profile snapshots, full operator-event coverage and measured quality/cost/latency/recovery. Recover older metadata only from contemporaneous evidence.
3. Implement the separately scoped durable M7 acceptance/currentness lookup and exact-SHA linkage to external Trust CI evidence. A local report remains advisory throughout.
4. Establish supported task-class cohorts, baseline review data, observation window, audits, and known failure outcomes. Count already documented evidence when it actually matches the exact tuple and producer contracts; calculate any remaining sample gap per tuple.
5. Design any broader task classes, activation or level progression as a separate versioned policy change with external authority and revocation/recovery semantics. This analysis makes no L3/L4/L5 activation claim.

## Focused acceptance tests for the write owner

Two merged PRs for the same task and a branch sync must not produce three accepted tasks. An actor of type `User` must not create an intervention. A partial zero must not create a fully autonomous session; no session evidence yields null rates. Explicit acceptance without an exact tuple stays historical evidence. Code-heavy accepted work remains visible with an unsupported-class diagnostic. One absent profile field prevents cohort grouping; two otherwise similar tuples with different prompt/provider/policy digests must remain separate. Unknown cost or rollback measurements remain null. No output authorizes a level change or external action.

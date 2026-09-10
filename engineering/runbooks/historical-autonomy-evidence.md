# Historical delivery and autonomy evidence accounting

`scripts/grok_history.py` summarizes one explicitly selected local JSON snapshot. It separates PR observations, identified work units, imported task-acceptance claims, measured operator interventions and exact-profile metadata. The implementation is in `.grok-stack/adaptive_grok/history.py`; the consumer installer includes both files.

Run the public synthetic example:

```bash
python3 scripts/grok_history.py examples/historical-evidence/synthetic.json
```

Keep real snapshots, source artifacts and detailed reports outside a public checkout. Select the snapshot explicitly and redirect stdout only to an operator-chosen private location when retaining a report:

```bash
python3 scripts/grok_history.py /private/evidence/snapshot.json > /private/evidence/report.json
```

The CLI reads that regular file once, prints deterministic JSON, and exits `0` on success. Invalid inputs produce a bounded schema error on stderr and exit `2`. It does not discover repositories, collect history, read credentials, fetch references, invoke subprocesses, write runtime state or authorize effects. Source-reference strings are opaque, untrusted data; their presence is a provenance claim, not verification that an artifact exists or says what the importer claims.

## Capture and normalize historical observations

1. Use an authorized read-only collector independently of this utility. Pin capture time, repository identity, default branch, explicitly selected delivery ref and its exact SHA. Retain paginated source snapshots and immutable source references outside the public tree. Mark `pagination_complete` true only after all PR pages for that source inventory have been obtained.
2. Preserve PR identity, merge state, merge target, original head SHA, landed merge SHA, merge timestamp and actor account type as independent observations. Record exact identity reachability against the pinned delivery ref separately. A default branch can be stale; an open stacked head can already be reachable in the delivery branch. False reachability means the recorded identity is not reachable; squash merges and cherry-picks can still contain equivalent code.
3. Classify `delivery_kind` as `product_change`, `branch_sync` or `unknown` from cited evidence. A branch synchronization remains a PR observation. It creates no new business task automatically.
4. Map tasks only when an existing task ledger, change package or other cited source supplies a stable work-unit identity. One task may link to multiple PRs; one PR may support multiple identified tasks. Do not assume every package is a unique business task or every PR is a task. Keep `task_inventory_complete` false while any historical work may remain unidentified, including when a complete PR inventory has an empty task list.
5. Record explicit acceptance separately from local validation. A merge, passing checks, deployment narrative, PR review or account type `User` does not establish human task acceptance. `User` may describe an agent using a user-owned client and does not measure operator intervention.
6. Recover costs, latency, regressions, rollbacks and historical profile revisions only from contemporaneous measurement evidence. Reference measurement artifacts in the task's `source_refs`. Leave unavailable values null; do not fill historical fields from present-day defaults. For interventions, cite event coverage directly in `intervention_source_refs`.

This is a single observation point. Reconcile evolving records in the collector before import. Exact duplicate repositories, PRs and tasks are deduplicated by their identities after canonical normalization; conflicting records with the same identity fail instead of selecting whichever appeared last. Duplicate counters describe repeated objects at each level, including repeats within duplicate repository objects.

## Input contract, version 1

Objects reject unknown and missing fields, except that `delivery_kind` is optional with default `unknown`, and profile fields may be omitted. Every nullable field must otherwise be present with null when unknown. Strings must be nonempty, bounded and free of control characters. Source refs are lists of opaque strings, sorted and deduplicated during normalization.

| Object | Fields |
| --- | --- |
| Snapshot | `schema_version`: exactly integer `1`; `captured_at`: timezone-aware ISO timestamp; `repositories`: list. |
| Repository | `repository_id`, `default_branch`, `delivery_ref`: strings; `delivery_sha`: lowercase SHA-1 or SHA-256; `pagination_complete`, `task_inventory_complete`: Booleans; nonempty `source_refs`; `pull_requests`, `tasks`: lists. |
| PR | `number`: positive integer; `state`: `open`, `closed`, `merged`; nullable `base_ref`, `head_sha`, `merge_sha`, `merged_at`, `merged_by_account_type`, `delivered_at_ref`; nonempty `source_refs`; optional `delivery_kind`. |
| Task identity | `task_id`: stable string within its repository; `pull_request_numbers`: list of positive numbers present in that same snapshot, possibly empty; nonempty `source_refs`. |
| Task acceptance | `acceptance`: `unknown`, `documented_validation`, `explicit_human_acceptance`, `rejected`; `acceptance_source_refs`: required nonempty for each non-unknown state, otherwise may be empty. |
| Task interventions | `operator_interventions`: nullable nonnegative integer; `intervention_coverage`: `unknown`, `partial`, `complete`; `intervention_source_refs`: list; nullable `session_started_at`, `session_ended_at`. |
| Task measurements | `cost_usd_micros`, `latency_ms`, `regression_count`, `rollback_count`: nullable nonnegative integers. A measured zero is distinct from null. |
| Task profile | `profile`: null or an object containing any subset of the fields below. Missing fields normalize to null. |

`delivered_at_ref` is Boolean or null. SHA values are lowercase 40- or 64-character hex; profile digests must be 64-character hex. `merged_at`, when known, requires merged state and cannot be later than capture. Unknown intervention coverage requires a null count. Partial and complete coverage require a known count and nonempty intervention source refs. Complete coverage also requires both session boundaries; start must be no later than end, and neither boundary may be later than capture. Partial coverage is a lower bound, including an explicitly measured partial zero.

Profile fields are `schema_version`, `repository_id`, `task_class`, `m7_change_class`, `m7_cohort_key_digest`, `provider_mapping_digest`, `agent_digest`, `validator_digest`, `provider_digest`, `model_digest`, `prompt_digest`, `policy_digest`, `runner_digest`, `holdout_digest`, `authority_digest`, `authority_ceiling`, and `expires_at`. `schema_version` is a positive integer when supplied, `expires_at` is a timezone-aware timestamp, and a non-null repository binding must match the containing repository. Other non-digest values are strings. Metadata describing unsupported task classes, versions, ceilings or expiry is retained with explicit compatibility diagnostics. The utility validates metadata shapes without constructing a factory autonomy tuple.

Bounds are 8 MiB of UTF-8 JSON; at most 100 repository objects; 20,000 raw PR/task observations in total, including duplicates; 100 entries per source-reference list; 2,048 characters per string; depth 12; 500,000 JSON values; and integer values no larger than `2**63 - 1`. Booleans are invalid counts. Duplicate JSON keys, fractional/nonfinite numbers, control characters and symbolic-link input files are rejected. These bounds also apply when calling `summarize_history(data)` directly, except that the byte limit applies to file loading.

## Read the report

The normalized digest is SHA-256 over ASCII canonical JSON (sorted keys, compact separators, escaped non-ASCII) prefixed by `historical-evidence-snapshot-v1` and a NUL byte. Ordering of repositories, tasks, PRs, references and PR links does not change the normalized digest. Timestamps normalize to UTC. Replay counters remain separate from the normalized content identity. No current clock or environment state is added to the result.

All counts concern the explicitly supplied repository scopes. `pull_requests_observed` and `merged_prs_observed` report deduplicated observations; `pull_request_total` is null when pagination is incomplete. `tasks_observed` counts distinct imported work-unit IDs. `task_total` is null when task inventory is incomplete. `explicit_acceptances_observed` remains visible even then, while `accepted_task_total` remains null. The latter also remains null when a complete task inventory contains unknown acceptance or only documented validation. Any known acceptance count still describes imported claims, not authenticated approvals.

Metric summaries expose known and unknown task denominators plus the sum of known measurements; a sum with no measured values is null. Intervention summaries expose complete, partial and unknown session counts. `observed_lower_bound` sums measured complete and partial counts, and is null when no count was measured. `complete_session_zero_intervention_rate` uses exactly `complete_session_count` as its denominator, excludes partial sessions, and is null when that denominator is zero. These are observed-record statistics, not full-history autonomy rates.

Every incomplete task profile lists `missing_profile_fields` and remains unassigned. Complete profiles form separate metadata buckets, including repository identity and every profile field in their digest. Changed prompts, agents, providers, policies, expiry or other fields produce separate buckets. `remaining_to_observed_30_floor` is arithmetic over imported explicit-acceptance claims for that one bucket; unsupported or expired metadata stays visibly diagnosed and is not eligible qualification. Never combine buckets or fill missing fields to reach 30.

All reports, including a synthetic bucket with 30 claimed acceptances, retain `m8_qualification: not_evaluated` and `authority_effect: none`. Local history imports cannot create M7 bundles, accepted outcomes, currentness, external Trust CI attestations, signed human approval, audit coverage or runtime activation. `qualification_gaps` lists the missing evidence categories; it is not an activation recommendation.

## Next capabilities and recovery

First finish source-backed task mapping and recover available acceptance and intervention evidence. Instrument future task/run identities, exact profile snapshots, complete operator-event windows and measured quality, cost, latency and recovery outcomes. Then implement separately scoped durable M7 acceptance/currentness and exact-SHA external evidence linkage. Build per-profile cohorts, observation windows, baseline samples and required audits from those bound records. Any activation, broader task class or authority progression requires its own authorized design, external policy and recovery controls.

The utility is optional and has no persistent application state. Roll back by removing its CLI/module and installer enrollment, or simply stop invoking it. Private snapshot/report retention and deletion remain with the operator; deleting a report has no runtime authority effect.

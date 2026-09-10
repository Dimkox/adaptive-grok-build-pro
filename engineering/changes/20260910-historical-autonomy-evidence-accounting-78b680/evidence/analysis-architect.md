# Architect analysis: offline historical evidence accounting

Route: `78b680187560`. Role: `architect`. Product files inspected read-only; this report is the only write. No private consumer identifiers or source content are included.

## Placement and compatibility

Use `.grok-stack/adaptive_grok/history.py` for pure validation/accounting, `scripts/grok_history.py` for a thin explicit-file CLI, and `tests/test_history.py` for synthetic fixtures and behavior tests. Existing `NODE-LOCAL-ROUTE-POLICY` owns the module and `NODE-LOCAL-VERIFIER` owns scripts/tests. No new architecture node, process service, network edge, dependency, database, policy, M7 contract or autonomy state is required.

Enroll `scripts/grok_history.py` in `scripts/install_into.py:MANAGED_FILES` and `grok_history.py` in `.grok-stack/config/managed.json:scripts`. The module is included automatically through the managed `.grok-stack` directory. Extend the existing installer payload assertion and exercise installed CLI help so an omitted entrypoint cannot silently pass. Do not enroll private snapshots or reports. General package inventory already includes ordinary source files automatically; no bespoke generated manifest is needed during implementation.

## Minimal versioned input

Prefer one normalized snapshot containing repositories and their separate PR/task observations. Collection remains a read-only operation outside this module. Suggested closed object shape:

```json
{
  "schema_version": 1,
  "captured_at": "2026-09-10T00:00:00Z",
  "repositories": [{
    "repository_id": "example/repository",
    "default_branch": "main",
    "delivery_ref": "main",
    "delivery_sha": "1111111111111111111111111111111111111111",
    "pagination_complete": true,
    "source_refs": ["private:snapshot-a"],
    "pull_requests": [{
      "number": 1,
      "state": "merged",
      "head_sha": "2222222222222222222222222222222222222222",
      "merge_sha": "3333333333333333333333333333333333333333",
      "merged_by_account_type": "User",
      "delivered_at_ref": null,
      "source_refs": ["private:request-1"]
    }],
    "tasks": [{
      "task_id": "example-task",
      "pull_request_numbers": [1],
      "acceptance": "unknown",
      "acceptance_source_refs": [],
      "operator_interventions": null,
      "intervention_coverage": "unknown",
      "cost_usd_micros": null,
      "latency_ms": null,
      "regression_count": null,
      "rollback_count": null,
      "profile": null,
      "source_refs": ["private:task-observation"]
    }]
  }]
}
```

`state` is `open`, `closed`, or `merged`; `head_sha`, `merge_sha`, account type, and delivery reachability may be null when unavailable. Reachability is a separately observed nullable Boolean: an open stacked PR can already be delivered, while a merged PR can target a non-delivery branch. Do not derive it from state or merge actor.

`acceptance` is `unknown`, `documented_validation`, `explicit_human_acceptance`, or `rejected`. A non-unknown acceptance needs source references. An importer asserting explicit acceptance still provides an untrusted claim, not an authenticated human receipt. Never infer it from GitHub `User`, an approval review, PR merge, automated tests, or a narrative claim of a successful deployment.

`intervention_coverage` is `unknown`, `partial`, or `complete`; counts are null if unknown. Complete coverage with a known count of zero is the only zero-intervention observation. Partial coverage can record a known lower bound but must not produce an autonomy rate. Unknown cost, latency, regressions and rollbacks remain null, and aggregation exposes known/unknown denominators.

`profile` is null or an object with nullable fields matching the existing exact M8 identity: `schema_version`, `repository_id`, `task_class`, `m7_change_class`, `m7_cohort_key_digest`, `provider_mapping_digest`, `agent_digest`, `validator_digest`, `provider_digest`, `model_digest`, `prompt_digest`, `policy_digest`, `runner_digest`, `holdout_digest`, `authority_digest`, `authority_ceiling`, `expires_at`. Sparse profile input can be normalized to all-null missing fields. Reject a non-null repository binding that differs from the containing repository. Only a complete profile can have an exact-profile accounting bucket; missing fields never form a shared wildcard cohort. Preserve noneligible historical task classes as observed evidence and report current `low_risk_text_only` eligibility separately.

## Validation and duplicate semantics

Bound input bytes, repository/observation counts, nesting and string lengths. Require ordinary JSON objects with recognized keys, reject duplicate JSON keys and nonfinite numbers, require timezone-aware timestamps, lowercase SHA-1/SHA-256 where applicable, and integers excluding Booleans for all counts. References are bounded opaque data, never paths to follow, commands to run, or URLs to fetch. Read the explicitly selected regular file once; produce stdout JSON and actionable stderr/exit failure without reading repository state, other paths, credentials or environment files.

Repository identity is `repository_id`; PR identity is `(repository_id, number)`; task identity is `(repository_id, task_id)`. Sort and deduplicate reference lists and linked PR numbers before canonical comparison. Identical duplicate observations count once and increase a duplicate-observation counter. Conflicting observations for the same identity fail validation; do not resolve by input order, merge fields opportunistically, or select the newest without an explicit versioned reconciliation rule. This snapshot is one observation point; evolving histories should be reconciled by the separate collector before import. Linked PR identities must exist in the repository snapshot, while multiple PRs may support one task and one PR may support multiple explicitly identified tasks. PRs themselves are never automatically tasks.

## Report and API

Expose `load_history(path)` for bounded JSON loading and `summarize_history(data)` for deterministic pure accounting, with a dedicated validation exception. CLI usage: `python3 scripts/grok_history.py <snapshot.json>`. Canonical sorted JSON output should contain a version, domain-separated normalized-input digest, explicit untrusted-evidence designation, inventory completeness, per-repository PR state/reachability counts, distinct task/acceptance counts, intervention and metric coverage, exact-profile buckets, and concrete missing fields. Do not inject wall-clock time into the report. A raw source-byte digest may accompany the normalized digest if collected during the single read.

For incomplete pagination, report `observed_count` and `inventory_complete: false`; do not emit an unlabeled final total. Overall completeness requires every repository snapshot to be complete. Empty complete inventories and missing task ledgers are valid, distinct states. A zero count means zero records observed in this input; it never establishes zero historical work.

Each full exact-profile bucket may expose `observed_explicit_acceptance_count` and `remaining_to_observed_30_floor`. Include the repository in the bucket key and never pool counts across profiles or repositories. Incomplete profiles remain individually unassigned, and their exact-profile coverage is unknown rather than guessed. Label the 30-task arithmetic as an accounting floor only. The report must always state `m8_qualification: not_evaluated` and `authority_effect: none`; importing even thirty perfect synthetic records cannot create validated M7 bundles, handoffs, cohort windows, measured quality/audit thresholds, signed security approvals, external attestations, or runtime activation.

## Verification and recovery

Prioritize tests for reordered equivalent input producing identical output, duplicate/conflicting identities, duplicate JSON keys, nullable metrics versus zero, partial intervention coverage, incomplete pagination, open-but-delivered PRs, repository/profile separation, task/PR many-to-many distinction, sparse profiles, malformed primitives, and thirty synthetic claimed acceptances retaining no authority. Test CLI error exit and installer entrypoint inclusion. Rollback is removal of the optional CLI/module; no production state exists to migrate or recover.

Transferable fact for the next subtask: exact historical profile coverage and imported acceptance claims are accounting evidence only; even a complete observed bucket cannot establish M8 qualification without the existing bound M7 and external evidence chain.

---
name: adaptive-delivery
description: Use for every routed software-development task. Reads the active route, dispatches only selected agents, enforces one write owner, and closes the task with fingerprint-bound verification and independent review evidence.
---

# Adaptive Delivery Controller

## Inputs

Read `.grok-stack/runtime/active-route.json`. It contains:

- intent, domains, risk, and complexity;
- required workflow skills;
- parallel read-only analysis agents;
- exactly one write agent or no write agent;
- independent review agents;
- quality profiles, human gates, and evidence kinds.

Do not substitute your own generic workflow when a route exists.

## 1. Establish the run

1. Run `python scripts/grok_status.py`.
2. Load every skill named in `workflow_skills`.
3. For `standard` and `high-risk` work, create a durable change package:

```bash
python scripts/grok_change.py start
```

4. Use the change package for scope, requirements, architecture, tests, decisions, release, rollback, and human approval evidence.

Micro changes may stay in chat if they are genuinely bounded, but still require verification and selected reviews.

## 2. Parallel analysis

Dispatch all `analysis_agents` whose work is independent. Give each agent:

- route ID and task;
- exact repository root;
- active change path when available;
- one narrow question;
- a report destination under `<change>/evidence/analysis-<agent>.md`.

Wait for all reports. Synthesize facts, conflicts, and unresolved decisions. Do not ask the user for facts recoverable from the repository.

## 3. Scope and design gate

Write or update the change brief, acceptance criteria, architecture, risk, and test plan.

When `human_gates` contains `scope_and_design_approval`, present the decision and stop before implementation. For ordinary low/medium-risk tasks without a named gate, proceed after recording a bounded design.

Transition durable changes:

```bash
python scripts/grok_change.py transition <change-id> scoped --reason "scope and acceptance criteria written"
python scripts/grok_change.py transition <change-id> approved --reason "approved or no named human gate"
```

## 4. Single-owner implementation

Dispatch only the route's `write_agent`.

The write agent must:

1. Read the change package and analysis reports.
2. Add a failing test or characterization test.
3. Implement the smallest coherent vertical change.
4. Run focused checks.
5. Return changed files, commands, results, residual risk, rollout, and rollback notes.

Do not spawn a second write agent for the same route. Review fixes return to the same write owner.

## 5. Verification

Run the route-selected profiles:

```bash
python scripts/grok_verify.py --mode pr
```

A failing check returns to the write owner. Do not record review receipts against a failing or stale tree.

## 6. Independent review

Dispatch all route `review_agents` in parallel. Each reviews the same final tree from its own perspective and writes a concrete report.

For every passing report, record the exact evidence kind:

```bash
python scripts/grok_review.py code_review --status pass --report engineering/changes/<id>/evidence/code-review.md
python scripts/grok_review.py test_review --status pass --report engineering/changes/<id>/evidence/test-review.md
```

Use `bitrix_review`, `security_review`, `data_review`, and `release_review` when requested. Any code change after review invalidates all receipts; rerun verification and affected reviews.

## 7. Close

Run `python scripts/grok_status.py`. Completion requires zero evidence gaps. For durable changes, transition to `ready` after verification and review.

Do not deploy, publish, merge, or perform external writes as part of closure. Those are separate, explicitly approved actions. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.

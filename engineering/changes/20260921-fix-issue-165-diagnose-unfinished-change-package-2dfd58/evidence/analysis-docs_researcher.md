# Documentation analysis — issue #165

Route: `2dfd5804553e`. Role: `docs_researcher`. Scope: repository contracts, lifecycle templates, retained-PR overlap, and durable handoff requirements. This is source/document inspection, not verification or independent review evidence. No tests, lint, compilation, Docker operations, product edits, commits, or publication were performed.

## Sources and observation boundary

- Read `START_HERE.md`, `PROJECT_STATE.json`, `AGENTS.md`, the active route, the active change package, and the route's adaptive-delivery, bugfix-workflow and api-event-change skills. `git fetch --all --prune` completed with exit 0.
- Issue #165 and related #125/#117 bodies were read from the parent-supplied snapshot `/home/pall/.cache/agbp-run/issues-wave-20260921/issues.json`; #165's recorded update is `2026-09-20T03:21:36Z`. These describe historical observations, not a fresh reproduction.
- Read the parent-supplied execution packet `engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/evidence/design-interruption-handoff-165.md` in the sibling research worktree. It explicitly narrows #165 to local, bounded diagnostics and disallows treating every draft or arbitrary TODO prose as a failure.
- Inspected retained refs `pr/141` at `92648fa6bf0db9bb9a9ae2b23a6765e4470bd06c` and `pr/134` at `25d7a2b958a1435bf794112e253bc3a6ab64dd73`, including their briefs/contracts and relevant diffs. No current external check conclusion or merge eligibility was inferred from these refs.

## Existing lifecycle and evidence contract

1. **A new draft is intentionally incomplete.** `.grok-stack/templates/change/state.json` starts at `draft`; `.grok-stack/templates/change/change-spec.yaml` and `generate_spec()` in `.grok-stack/adaptive_grok/spec.py` create `UNKNOWN` objective target/success metric and empty criteria. `requirements.md` contains the literal unfinished Given/when/then checklist. These are expected initial scaffolding, not evidence of corruption or a dead author.
2. **Meaningful scope precedes implementation.** Adaptive-delivery section 3 requires the brief, acceptance criteria, architecture, risk and test plan before `scoped` and `approved`. The transition graph in `.grok-stack/adaptive_grok/change.py:18` then proceeds through implementing, verifying, reviewing and ready, with explicit blocked/rework paths. The current `transition()` checks graph legality and appends history; it does not enforce document completeness or capture the product diff.
3. **Shape validity is different from gate completeness.** `spec.py:746` rejects unknown objective fields and empty acceptance criteria in gate mode, and imposes additional red-risk requirements. `.grok-stack/adaptive_grok/verification.py:752` selects gate validation in PR/release mode, with its existing explicit exemption. The M1 plan (`docs/superpowers/plans/2026-08-26-m1-typed-intent-evidence.md:147`) already distinguishes draft validation from gate validation. A status inspector should expose unfinished fields cheaply without changing those semantics.
4. **Evidence obligations and passing evidence are different.** The route requires verification, code review and test review. AGENTS requires observed verification and independent reports bound to the final fingerprint. A `not_run` entry with a concrete reason makes an obligation's state explicit; it cannot satisfy a passing receipt, ready state, or merge check. A missing row or bare placeholder says neither that a command passed nor why it has not run.
5. **Current templates omit a useful checkpoint.** `.grok-stack/templates/change/evidence/README.md` only says where reports and machine receipts live. `start_change()` captures route/task/time and draft history, but no branch, HEAD, diagnostic base or product-state observation. This is the bounded missing handoff surface identified by #165.
6. **Local and remote continuity differ.** `AGENTS.md:10` and `START_HERE.md:67` require durable repository/PR handoffs; runtime routes and receipts are intentionally machine-local. A locally appended record helps another session in that worktree. Another clone cannot discover uncommitted files or an unpublished checkpoint. Remote continuity requires a separately authorized committed/published record; a local status command cannot provide crash immunity or cross-host discovery.

## Historical quotations versus unfinished current evidence

Issue #165 quotes the old standalone `<!--RUNTABLE-->` under a mandatory disposable-exit heading. The current #155 file `engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/evidence/postgres-evidence.md:279` instead has a named command/protocol, four run rows, results and explicit limitations on the original path/status fingerprint. The later file sections preserve superseding evidence. This inspection does not revalidate those historical executions.

The diagnostic should inspect current typed fields and explicit active template slots or mandatory-evidence sections. A standalone unresolved marker in an active mandatory slot is unfinished work. A marker inside a code fence, inline quotation, historical incident description, test fixture or superseded record is not automatically a current obligation. This report itself quotes the marker; scanning every byte under `evidence/` would therefore create a false finding against the analysis intended to explain it.

Do not ban `TODO` or `TBD` anywhere in prose. Do not infer an empty mandatory table was satisfied merely because another historical section contains a successful run. Link an obligation to its current run record or explicit `not_run` reason, and preserve prior failures/superseded observations. Exact parser/section conventions should be documented by the implementer so authors can predict which text is active.

## Retained work boundaries

| Work | Existing retained scope | Boundary for #165 |
| --- | --- | --- |
| [PR #141](https://github.com/Dimkox/adaptive-grok-build-pro/pull/141), [issue #125](https://github.com/Dimkox/adaptive-grok-build-pro/issues/125) | Counts/maps AC, INV and FORBID evidence references; fails the gate for unmapped declared criteria; keeps draft reporting descriptive. Preserves historical AC-only coverage fields and the Trust CI v1 attestation projection. | Detect incomplete package fields early. Do not implement a second coverage engine, redefine signed coverage, or claim a cited reference proves an execution happened. Coordinate any shared `spec.py` or verifier changes with this retained implementation. |
| [PR #134](https://github.com/Dimkox/adaptive-grok-build-pro/pull/134), [issue #117](https://github.com/Dimkox/adaptive-grok-build-pro/issues/117) | `docs/review-report-v1.md` defines bounded structured claims, confined regular report files, source-span digests, linked revisions and report-byte binding. Execution provenance is explicitly `self_reported_unverified`; shape checks do not authenticate execution. | Add concise package findings before review-receipt recording without replacing this report contract or promoting checkpoint/run-row prose into verified execution. Preserve receipt pass/fail meaning and fingerprint freshness. |

PR #134's report contract is retained source at the observed ref; it is not present as a delivered current-tree guarantee merely because the branch exists. Likewise, #141's broader coverage is adjacent work, not authority to widen this slice silently.

## Minimal durable handoff requirements

- At package creation, record change/route identity, timestamp, branch, exact observed HEAD, an explicitly named diagnostic base, and `draft; implementation not started`. Unknown Git facts must remain unknown.
- At the first implementation transition, append a checkpoint with the same identity and observed product-diff state (clean, dirty with bounded paths, or unknown), plus the next action. Keep earlier observations; do not overwrite history or auto-publish.
- Make required evidence obligations explicit and associate each with a measured run record or `not_run` plus reason. Keep incomplete obligations visible independently of receipt freshness.
- Return lifecycle stage, findings with field/path context, branch/HEAD/base and observation time from the cheap nonmutating status surface. An orphan candidate is a recovery hint, not a diagnosis of a crash or proof that no agent owns the work.
- Report zero-ahead only against a known, resolvable, clearly named base. In this worktree, HEAD was `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` on `fix/issue-165-interruption-status`; `git rev-list --count 90078959ff816068af374ad42f4bb80fdbaec866..HEAD` returned **6**. The route base therefore is not the task's initial HEAD. If a task-start checkpoint is used to count new task commits, expose it separately from the route/verification base rather than silently changing base semantics.
- Inspect only the active bounded package and allowed regular files. Missing/malformed/inaccessible content and unresolved Git/base information need named diagnostics, not guessed values or arbitrary symlink/log reads. Another worktree's contents are outside this first feature's discovery scope.

## Shared-memory facts for the single write owner

The current package is legitimately a draft; unknown fields become useful recovery findings only with their lifecycle and Git observations attached. A truthful `not_run` reason closes an information gap but never an evidence gate. Historical template quotations must remain readable without making unrelated current evidence incomplete, and checkpoint HEAD must be named separately when it differs from the route base.

Suggested durable decision after implementation proves the approach: use explicit current obligations and stage-aware diagnostics, preserving historical evidence and unknown observations, because broad placeholder scans confuse analysis/reproduction text with unfinished work. Only the single write owner should promote this fact into `decisions.md` under the route's shared-memory rule.

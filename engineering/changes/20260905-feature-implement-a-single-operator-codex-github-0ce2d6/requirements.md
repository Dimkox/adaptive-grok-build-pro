# Requirements — single-operator design-partner pilot

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Product requirements

1. Produce the five immutable outputs `IssueSnapshotV1`, `CandidateChangeV1`, `CandidateValidationV1`, `PullRequestProposalV1`, and `DesignPartnerOutcomeV1` in that order.
2. Derive policy only from a trusted exact target profile. Issue text and model output are data, never instructions to the controller.
3. Start Codex at most once. Any provider timeout, crash, invalid candidate or semantic non-pass is terminal for this run.
4. Create a private exact-base clone with `umask 077`, `--no-local`, `--no-hardlinks`, sterile Git configuration and no remote before model execution.
5. Prove the actual Codex workspace-write sandbox and network denial before the invocation. Run candidate tests in a credential-free no-network sandbox.
6. Seal one single-parent candidate with trusted Git inspection and reject path/mode/size/base/tree violations.
7. Run only the trusted absolute-Python unittest argv, then deterministic semantic checks on the unchanged candidate.
8. Persist each prepared external intent before effect. Restart or ambiguity permits one read-only reconciliation, never an automatic second write.
9. Require literal operation-digest resources for separate branch-push and draft-PR grants. Exact grants do not authorize merge, close, deployment or Trust CI.
10. Report `merge_gate_unavailable` honestly when the landing repository lacks its App-owned exact-SHA check/profile.
11. Expose the exact run as `prepare`, `publish-branch`, `publish-proposal` and read-only `status`; every effect-capable phase is unavailable without both `--live` and one closed owner-only config.
12. Reopen only the deterministic private job workspace across CLI processes, after revalidating owner/mode/no-symlink, exact HEAD/tree, clean state, no remote/alternate, independent objects and unchanged source.
13. Bind runtime grants independently to the current control origin, route/change, Git HEAD and adaptive tree fingerprint. Branch and proposal grants are literal, distinct and loaded only at their own phase.
14. Prefer one bounded Codex app-server thread/turn using the host ChatGPT capability without reading/copying auth bytes. Disable MCP/web/shell-env inheritance, require the exact returned workspace/no-network confinement, reject every server request, and retain credential-isolated API-key exec only as an optional closed mode.
15. Provide only the exact pinned GitHub reads, one non-force candidate-ref push and one draft-proposal create. Do not expose a generic raw API or any force/merge/close/delete/tag/comment/label/deploy operation.

## First live issue semantic gate

- Root and five locale pages show published version `v2.0.14`, and root JSON-LD version is `2.0.14`.
- Root page contains `Governed Agentic Software Factory — Offline Technical Preview`.
- Root page does not claim Enterprise-ready, production autonomy, M8/M9 activation, live provider/publisher, hosting/indexing, or deployment authority.
- The `.htaccess` CSP authorizes the exact changed inline JSON-LD hash and keeps the existing restrictive directives.
- The full configured unittest suite passes; no file changes during validation.

## Governance context

Applicable architecture rules include `FIT-ARCHITECTURE-EXPANSION-RISK`, `FIT-FACTORY-NO-TRUST-OR-EXTERNAL-EDGE`, `FIT-TRUST-CI-SEPARATION`, and secret/external-integration fitness rules. The new network/secret/datastore/trust crossings escalate the exact diff to red; the component is a separate operator-pilot trust domain and does not weaken factory or Trust CI boundaries.

No intentional debt may hide a core-path authority, isolation, replay, data-integrity or exact-SHA defect. Diagnostics, portability and rare non-authority error variants are backlog after MVP.

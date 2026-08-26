# Design self-review

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Review scope: canonical design, durable package, five analysis reports, and the new decision entry.

## Result

Pass for the written `scope_and_design_approval` gate. This is not implementation approval, verification evidence for runtime behavior, or merge authority.

## Placeholder and completeness review

- The canonical design and authored package projections contain no scaffold tokens, unresolved metric/target values, empty prose bullets, or example acceptance text.
- `change-spec.yaml` validates at red risk with domains `ai` and `security`, five acceptance criteria, five invariants, four forbidden outcomes, architecture/security approval scopes, and no unmapped acceptance criterion.
- Historical analysis statements that quote the former scaffold state remain evidence of the pre-write baseline; they are not live package fields.
- All five route-selected reports and the canonical design referenced by the typed spec exist.

## Contradiction review

- Resolved M1 wording: commit `48cb973` is an M1 foundation, while repository-wide criterion receipts, holdout/attestation binding, staleness, adoption, and exemption enforcement remain the first post-review milestone.
- Resolved roadmap/external-write tension: M7-M9 states are unreachable through M6 and require later evidence plus separate authority.
- Resolved process-count/ownership ambiguity: fixed systemd counts provide defense in depth; PostgreSQL leases and fencing enforce correctness.
- Resolved worktree/isolation ambiguity: the trusted workspace manager brokers shared Git state and OS isolation; a worktree directory alone is never presented as a security boundary.
- Resolved provider/native-protocol ambiguity: Codex and Grok native streams are private to explicit adapters; the factory owns a separate versioned canonical protocol.
- Resolved approval ambiguity: route design approval, local delegated grants, and Trust CI signed human approvals remain distinct authorities.

## Security review

- Prompts, repository content, notes, logs, tool output, native events, and model results are consistently classified as untrusted data.
- The design does not claim prompt-injection prevention. Immutable packets protect approved control fields, while capabilities are enforced outside the model.
- Repository subprocesses receive no credentials and no network; provider authentication and egress terminate at an isolated provider-control boundary.
- Raw reasoning, scratchpads, unrestricted prompts, provider-native streams, and unrestricted stdout/stderr are excluded from durable storage by allowlist.
- Provider selection is persisted before dispatch. Unsupported or unavailable providers fail typed and never trigger silent fallback or capability downgrade.
- Missing trustworthy usage or pricing blocks further calls and cannot be interpreted as zero cost.
- Factory and Trust CI databases, credentials, policy, holdout, signing, approvals, and verdict authority remain separate.
- Push, PR, merge, release, deploy, systemd installation, connectors, and production actions are absent capabilities through M6.

## Limits and recovery review

- Readers are capped at 20 globally and 10 per repository; exactly one global application writer is fenced.
- Infrastructure retries are at most two after the initial attempt; semantic repairs are independently capped at three and return to the same writer.
- Four-hour wall time and USD 25 cost limits aggregate across attempts and repairs.
- Packet digests, exact state, idempotency, lease generations, heartbeat/expiry, late-result rejection, kill switches, and reconciliation are all explicit.
- Notes, events, output, artifacts, logs, queues, and retention require hard bounds; no unbounded loop remains in the design.

## Scope review

- Changed product content is limited to one design specification, the exact active package, and a two-sentence decision entry.
- No runtime source, dependency, migration, root packaging marker, GitHub Actions file, systemd unit, or implementation-plan document was added.
- No second package was created and no package-start command was used.
- No provider execution, credential read, push, PR, merge, release, deploy, installation, production mutation, or other external write occurred.
- Package state must remain `scoped` pending explicit user review; it must not transition to implementation approval or `ready` in this change.

## Checks recorded before commit

- `python3 scripts/grok_spec.py validate --change-id 20260826-model-agnostic-autonomous-factory-355689`: pass; digest `56b7f1c85e8cfa85c4e4530844208a250c9f03fa0ebac02c20069984fd068451`.
- `python3 scripts/grok_spec.py summarize --change-id 20260826-model-agnostic-autonomous-factory-355689`: red risk, five acceptance criteria, five invariants, four forbidden outcomes, zero unmapped criteria.
- `python3 scripts/grok_spec.py map --change-id 20260826-model-agnostic-autonomous-factory-355689`: all five acceptance criteria mapped.
- Authored-file scaffold scan: pass; quoted historical scaffold facts exist only in read-only analysis reports.
- `git diff --check`: pass after normalizing report whitespace.

Final repository verification, package transition, changed-file review, and commit identity are recorded after this report is written.

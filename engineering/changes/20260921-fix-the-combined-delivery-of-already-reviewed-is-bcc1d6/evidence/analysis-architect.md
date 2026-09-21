# Architect analysis: reviewed repair batch

Route: `bcc1d645c438`. Role: selected `architect`, independent of the implementation owner.
Scope: static integration design for the six entries in `../candidates.json`, covering eight issues.
This report is design evidence, not a review receipt, completed verification, or merge authority.

## Observed integration boundary

- New base is `839d3aa26bc90417424d814ee48d8b5cd3be367e` (PR170).
- All candidates use source base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`.
- Both commits have the identical Git tree `e2a807845c77af0c6023c53fcd30972ede9fb8bd`; their complete tree diff is empty.
- The manifest enumerates 19 product/test paths, all unique. No candidate needs another candidate's product changes to apply.
- Inspected the actual implementation deltas and issue-specific final review reports. Installer, fingerprint and schema-reference repairs have renewed passing reviews but still need final full verification.
- Router, receipt schema and migration tests retain their recorded completed candidate verification. Those results do not certify the combined commit.
- Current bootstrap still describes #155 as unpublished and main as `90078959`; this is stale handoff content inherited through the merge, not the current source identity.

## Bounded design

The selected `integration_implementer` should materialize only each manifest entry's exact product blobs from its pinned candidate commit. Whole-branch cherry-picks would repeatedly import conflicting shared handoff documents and obscure the final scope.

Copy the six named change packages without rewriting their historical reports, failed reviews, repair logs, original route identities or verification claims. Preserve the original candidate SHA, source base, product blob identity and package provenance in the combined package. This makes imported evidence attributable without pretending its receipts bind the combined tree.

Reconcile `START_HERE.md`, `PROJECT_STATE.json` and the root README against the new base once. Record PR170/#155/#164 delivery using actual observed GitHub facts, name this batch as the active source task, and retain dated individual candidates under its provenance/history. Preserve immutable release hashes, product VERSION, deployed runtime observations, unproven operational outcomes, architecture links and unrelated retained work.

Append only relevant new decisions/mistakes, deduplicating shared history by content. Do not replace these shared files with one candidate's snapshot. Do not copy the consumer AGENTS template over the factory-root AGENTS contract.

The additional ingress package is an immutable accepted-operation record from its named commit. Import only that package and deliberately reconciled public status facts; do not activate units, execute embedded commands, import runtime grants, copy secrets or change the accepted host configuration.

## Interactions requiring combined evidence

| Boundary | Preserved behavior and integration check |
| --- | --- |
| Router and shared JSON persistence | `matched_keywords` is optional and bounded; old routes still parse. Fingerprint's ASCII escaping changes serialized presentation, not parsed Unicode values, route authority or canonical receipt digest semantics. Inspect persistence roundtrips together. |
| Receipt schema and workflow reader | Schema adds existing `bitrix_review` and `data_review` kinds; its parity test imports both runtime registries. Router changes the reader's optional keys without changing its receipt registry. Unknown receipt kinds must still fail. |
| Fingerprints and receipts | Only proven-untracked literal top-level `.qwen/tmp/` descendants are exempt. Tracked/template/product paths, POSIX lookalikes, non-UTF-8 bytes and uncertain ownership remain covered according to the reviewed implementation. Bind new combined receipts after source/document freeze. |
| Installer and changed tooling | The payload now includes the combined router, reader, utility and templates. Manifests must bind emitted bytes; reusable consumer-source rendering, valid relocation refusals, existing-target preservation and rendered links must pass on this actual payload. |
| Schema comparator and receipt schema | Path-first resolution retains declared-ID fallback and conservative dependency closure. Widening the receipt enum must remain an ordinary compatible schema extension; bounded diagnostics must not truncate dependency traversal or late refusals. |
| PostgreSQL tests and merged 021 | #166 changes one test file only. The populated prefix test derives its pending suffix from packaged resources, which remain 001–021 here. Preserve real ledger, rows, function identity/ACL, advisory admission timeout and retry assertions. |

The #162 trusted-validator successor is explicitly excluded. Local schema parity does not establish deployed Trust CI validator parity, and combining candidates must not reintroduce its excluded Trust CI source patch. Issues #165/#163, migration022 and retained PR137's separate comparator work remain outside this batch.

## Acceptance criteria

1. Exactly the 19 manifest product/test paths match their pinned candidate blobs; every additional diff is explicitly accounted for as combined handoff or preserved evidence. No out-of-scope source changes are introduced.
2. SQL resources 001–021, production migrator, `trust-ci/` source, architecture policy/model, release artifacts and authority configuration remain byte-identical to new main. No dependency, provider activation, database operation or deployment is added.
3. All six issue packages preserve original evidence and repair history. The combined manifest maps every issue to its exact source and package; old PASS/FAIL results retain their actual commit and scope.
4. Fresh-clone entrypoints consistently name the combined branch, current observed main and next action without losing release/runtime/history records or presenting host-local grants as Git content.
5. Run the mandatory combined `python3 scripts/grok_verify.py --mode pr` on the completed tree, honoring the reserved CPU lane. Required base/contracts/data/integration profiles and real disposable PostgreSQL tier must complete with their actual results disclosed.
6. Dispatch every selected independent reviewer after implementation and verification: code, test, security, data **and release**. Freeze the final repository contents and bind all six required evidence kinds, including verification, to the final fingerprint; `grok_status.evidence_gaps` must be empty before local completion.
7. Publish through one PR and require the App-owned policy-epoch check on its exact current head/base, plus applicable signed scopes. Close the eight issues only after their repairs are delivered; old candidate PRs are superseded through explicit linked disposition, not claimed as independently merged.

The existing focused RED/GREEN evidence already establishes the individual defects; unchanged exact blobs do not require manufacturing another RED run. A new integration defect goes back to the one selected writer with a targeted regression and renewed affected reviews.

One combined full gate and its independent reviews replace the still-pending isolated final gates for these exact imported candidates. This consolidates delivery evidence; it does not waive checks or promote earlier heads into current authority. Any later content change invalidates fingerprint receipts, and any new base/head requires the applicable external check again.

## Authority and recovery

The named scope/design gate concerns the same eight repairs already explicitly delegated by the user. The coordinator must record that inherited authorization and this bounded integration choice; this report does not invent consent. Branch push, PR writes, merge and issue disposition remain separately exact-granted operations. No migration or production external write is necessary for implementation.

Before publication, retain the candidate branches and abandon or repair only the isolated combined branch. After merge, any necessary reversal is a new reviewed PR against current main; reverting this batch's product delta must retain merged SQL resources 001–021 and their ledger compatibility. The batch contains no database rollout to reverse and importing the ingress record does not authorize stopping its accepted bridge.

If rolling the router reader back to a version without `matched_keywords`, regenerate affected machine-local routes through that version rather than feeding new-format records to the old closed reader. Fingerprint-changing rollback needs fresh local evidence and grants. Installer rollback must respect existing consumer ownership; this change does not authorize overwriting installed consumers.

## Evidence limits and handoff fact

Performed only static Git/file/JSON reads; no tests, imports, compilation, lint, Docker, receipts, commits or external mutations. Applied the route's adaptive-delivery and listed domain skill boundaries. Wrote this report only.

Fact for the coordinator's shared-memory record: the merged predecessor and all six candidates' source base have identical complete Git trees, and their 19 product paths are disjoint. Exact-path extraction therefore preserves reviewed bytes while allowing one current combined gate; shared handoff files still require deliberate reconciliation.

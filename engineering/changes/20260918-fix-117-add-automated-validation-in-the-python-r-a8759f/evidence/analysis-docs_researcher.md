# Documentation and workflow analysis — #117 review-record evidence

## Evidence examined

- GitHub issue #117, including its four contradictory report revisions, its corrected clean-room measurements, the malformed JSON-string probe passed to a dictionary-oriented analyzer, and the report that conflicted with the actually committed test-review artifact.
- Current `scripts/grok_review.py`: it checks only that the named report is a file, then records the caller-supplied review status.
- Current `.grok-stack/adaptive_grok/receipts.py::write_receipt` and evidence validator: a receipt binds the caller-provided report path/status to route, tree fingerprint, and current spec/architecture/governance bindings; validation checks the receipt envelope and freshness. Neither opens nor parses the report or verifies command execution, report content, citation support, or reviewer identity.
- Existing review guidance and reports: reviewer briefs request concrete findings and the receipt CLI does not define a structured evidence-record format. No canonical reusable report template exists on this route's base tree.
- The separate #124 candidate in `/tmp/adaptive-fix-reviewer-scratch`, especially `engineering/reviews/review-report-template.md` and the code/test reviewer briefs. That template asks for exact command, working directory, output excerpt, exit status, and the limited conclusion for each execution-backed claim, while explicitly saying that the receipt checks presence/fingerprint only and cannot authenticate those statements. Its implementation candidate is not present in this route's base tree and must not be assumed as a dependency.

## Implications for this change package

Keep #117's implementation centered on a versioned, machine-readable record contract consumed by `grok_review.py` (or a helper it invokes), with regression tests for missing/malformed records, invalid command evidence, repository path/revision/span resolution, and mismatched probe-input shape. Define which report forms remain accepted during any compatibility period; do not silently convert a legacy prose report into verified execution evidence. Package acceptance criteria should say which invalid records are rejected versus retained as explicitly unverified, and at which boundary that happens (receipt authoring, evidence validation, or durable promotion).

Coordinate the record schema with #124's execution-evidence template: use the same fields and vocabulary where practical, and revise the #124 template if implementation chooses different names or requirements. The template remains useful authoring guidance, but its unmerged presence cannot be treated as enforcement. Because the candidate targets differ and the current #117 route is API-only, avoid adding the #124 reviewer-scratch policy, prompt rewrites, or cleanup rules to #117's scope; instead ensure the verifier can consume reports that follow the #124 template once that candidate is integrated. Record any ordering/dependency decision in the package before implementation.

The report's evidence model should distinguish at least (a) a machine-checked structural/source fact, (b) a declared execution record, and (c) an inference. A repository path can be checked against its declared commit/tree and a cited span can be checked against bytes at that revision. A command string, quoted output, exit code, cwd, timestamp, or self-authored JSON record cannot by itself prove the process ran: when the evidence does not originate in a trusted capture boundary, label it self-reported/unverified and do not promote it as independently measured evidence. A verifier that only parses fields or checks that a path exists must not claim to have established semantic support for the conclusion.

## Boundaries and cautions

- Repository-local validation can reject missing paths, invalid paths/revisions, incomplete command records, malformed probe inputs, and incompatible structured revision fields. A local assertion such as `verified: true`, a report digest, or a fingerprint-bound receipt is still an assertion unless it is bound to trusted tool-execution capture.
- Path existence is revision-scoped. `git cat-file -e <commit>:<path>` checks the named commit; `git log --all -- <path>` is bounded by fetched local refs. Neither proves absence from every remote, unfetched ref, or the host's disk. Deleted-path citations need an explicitly named historical revision.
- Comparing structured report revisions can flag changed verdicts, evidence IDs, paths, inputs, or outputs and require re-derivation. It cannot promise to detect every natural-language contradiction. A correction is not automatically fabrication, but it must preserve the prior revision and bind the changed claim to fresh evidence.
- “Fresh-clone run” is stronger than a local status claim only if clone identity, source/base, exact tested commit, and the actual captured command result are established. A line of narration that says “fresh clone” is insufficient.
- #124's reviewer-tree-integrity rule addresses accidental mutation of the checkout and private scratch discipline. It does not establish factual truth of assertions. Conversely, #117's record verifier should not be described as preventing mutation unless it independently enforces the relevant filesystem boundary.
- Local review receipts remain workflow evidence and cannot attest to reviewer independence/identity, truthful unobserved actions, external Trust CI checks, signed approval, or merge authority.

## Suggested package updates

The current #117 brief, requirements, change spec, and test plan are still empty scaffolds. Before implementation, make the acceptance criteria concrete and mutually consistent: specify the evidence-record schema/version; how `grok_review.py` consumes it; exact-tree path and line/span checks; treatment of deleted/historical paths; validation of command/probe shape and the actual execution-provenance trust level; revision-chain/contradiction behavior; legacy-report behavior; and explicit failure messages. Add tests proving both rejected false evidence and valid bounded evidence, including malformed-probe input and a correction whose source revision legitimately changes. State in rollback/release notes that this is local workflow validation, not identity or merge authorization.

No product code or other files were changed for this analysis.

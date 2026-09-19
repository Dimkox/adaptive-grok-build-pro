# Fix #117: Validate structured review evidence before recording receipts

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260918-fix-117-add-automated-validation-in-the-python-r-a8759f`  
Risk: yellow; local workflow evidence only.

## Problem

`grok_review.py` accepts an existing report path and caller-supplied pass status without reading the report. Absolute paths and symlinks can escape the repository; citations and execution claims are not checked; the stable receipt slot overwrites report identity.

## Outcome

Durable pass receipts only accept bounded, repository-confined, versioned JSON review reports with structurally valid claims and citations. Receipts bind the exact report bytes and the validator checks that binding later. Locally declared commands remain self-reported and explicitly unverified.

## Scope

### In scope

- Confined regular report file validation, including absolute/traversal/symlink escape rejection and a size bound.
- Versioned claim records for source citations, execution records, and inferences; validate source paths/spans against the current tree. Probe records use only the named `adaptive_grok.architecture.unsupported_schema` v1 object contract; other IDs and JSON-string schema inputs fail closed.
- Report digest in receipt and digest/existence validation in `validate_evidence`.
- Linked report revision metadata with a prior report digest; derive the exact changed/added claim IDs and status fields from predecessor comparison. Require a different evidence payload for changed claims, reject silent removals (same-ID inference retirement is the explicit representation), and require fresh changed claims for status transitions. These are deterministic consistency checks, not proof that evidence is true or cryptographic append-only protection.
- Regression tests for accepted and rejected evidence.

### Out of scope

- Proving a command actually ran, the author's identity, semantic correctness of a claim, or a clean-clone environment from self-authored local data.
- Trust CI, signed approvals, merge authorization, issue closure, or changing the deployed trust boundary.
- Coupling to the separate #124 package; its guidance may align later but is not a dependency.

## Constraints

- Legacy prose reports cannot produce a durable passing receipt.
- Receipt freshness remains tied to the exact repository tree and report digest.
- Unsupported or narrative-only execution assertions stay unverified; no wording may promote them to verified evidence.
- The v1 format and exact field bounds are documented in [`docs/review-report-v1.md`](../../../docs/review-report-v1.md); revision links and command records remain author-supplied local data. The report status must match the requested receipt status.

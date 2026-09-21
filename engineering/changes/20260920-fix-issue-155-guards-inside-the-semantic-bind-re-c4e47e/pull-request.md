# fix(factory): explain repair-child binding rejections

Repair-child precondition failures previously returned SQL NULL and surfaced as an
`invalid_object` parser error. Add migration 021 to return twelve fixed rejection
reasons, classify refusals before parsing a binding, and keep real malformed payloads
separate. Legacy NULL is handled before parsing too, so its traceback no longer
retains the misleading parser exception. Acceptance predicates, locks, grants and
immutable migration resources 001–020 are preserved.

Use request/server clocks in the affected PostgreSQL fixtures so the evidence suite
can run beyond the authority freshness window without expiring its own valid inputs.
Refresh the bootstrap handoff and retain a read-only investigation for the next
external pilot; no target site, provider or installed database was changed.

Validation on the corrected product:

- Full route verifier PASS: 785 root tests, 80% measured coverage, selected factory
  and pilot checks, mandatory PostgreSQL tier and source stability.
- Four consecutive PostgreSQL passes on the same byte-sensitive product manifest:
  358.330 / 375.076 / 378.336 / 366.498 seconds. Each reports 779 tests with two
  conditional environment skips and actual database restart/reconciliation.
- Independent code, test, security and data reviews PASS. The NULL regression was
  independently reproduced red against old code and green against the correction.

The [final evidence archive](evidence/final-20260921/README.md) discloses the skipped
empty-cluster role scenario, installed-PDF-parser condition, optional pinned-Codex
sandbox case, and unconfigured workflow artifacts. Final whole-tree receipts must
be current on the frozen delivery commit. This source PR does not claim the separately
tracked shipped 001–020-to-021 upgrade scenario (#166) has been added.

Recovery retains all applied migrations and uses a reviewed additive correction;
removing 021 from an upgraded installation is not a valid rollback. Publication,
deployment and App-owned merge eligibility remain separate operations/gates.

Fixes #155. Fixes #164.

# Architecture

Current verifier executes later checks after a decisive refusal; ordinary fast mode still discovers Core and is not a bounded smoke.

Bounded design: default fail-fast at completed-check boundaries only for PR/release, sharing existing closed status/skip allowances. Explicit keep-going is diagnostic, not a bypass. Never run full QG on an incomplete prefix. Stop later execution but always reach source-stability, unchanged full admission and eligible receipt finalization. Actual failure is retained; unexecuted checks use existing SKIP plus not-executed/blocked-by string details, never fake executed discovery failure. Invalid spec/architecture/governance and source mutation preserve receipt refusal.

Reuse existing local-preflight modules verification.py, quality_gates.py, python_test_runner.py and scripts/grok_verify.py. Named fast smoke requires explicit targets, no-record, clean committed HEAD, actual Core environment and budget1–180s; it cannot qualify PR/release. Preserve integrated Core measurement/cancellation contracts rather than introducing a new runner merely to remove small coverage export overhead.

Successful scope, strict report/v1 reference/wrapper, external Trust CI and branch protection remain unchanged. Metadata stays inside existing details; no API/event/schema/service/dependency expansion or architecture ownership change.

Rulings: keep ordinary fast and explicit landing paths compatible; optimize PR/release. A bindable stable refusal records FAIL; invalid authority has an explicit recording refusal rather than forged binding. User approved the bounded proposal and route has no named human gate.

User-approved delivery order: bounded committed-HEAD observations → both independent selected reviews → persist reports/commit/freeze → one final full local PR gate in parallel with external App-owned exact-head Trust CI after exact delegated UNVERIFIED transport. The final run owns scope admission and fresh receipts; controls and historical full PASS do not. Ten minutes remains an unconfirmed target; the current serial PostgreSQL flow and Core/PostgreSQL sequencing are unchanged.

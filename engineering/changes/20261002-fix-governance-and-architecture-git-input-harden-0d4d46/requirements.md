# Requirements — Fix governance and architecture Git input hardening: explicit repository object binding, controlled Git environment, filter-free committed reads and pinned bounded regular-file projections.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- AC-001: a local or registered linked worktree stays bound to its explicit Git directory even with foreign ambient Git overrides.
- AC-002: committed reads accept full native-format commits and refuse abbreviated/missing/wrong-kind identities, unsafe entries and executed replacement/filter bytes.
- AC-003: fixed projections require bounded regular non-symlink UTF-8 files, count unique input bytes once and refuse mutation before output.
- AC-004: exact governance input mismatch, hidden mutation and repository-authored external rule claims block handoff; clean/current-HEAD and frozen schema remain gates.
- AC-005: current full PR verification and independent reviews remain controller-owned requirements.

## Failure and edge cases

- Cover SHA-1/SHA-256, registration/backlink mismatch, ancestor discovery, ambient object/config overrides, gitlinks, replacement refs, configured filters, stream caps, symlink/FIFO/device, invalid UTF-8, oversized/shared-budget input and path/content/root races.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- No canonical rule/example/debt edits or authority claims. Existing example and debt external gates stay intact; active rule claims gain the equivalent explicit external-authority refusal.

## Non-functional requirements

- Security: controlled Git environment and explicit repository resource binding; descriptor-relative no-follow projection reads.
- Reliability: final rechecks refuse stale identity/content; no product mutation during projection publication.
- Performance: keep existing Git/io bounds and batch blob reads; focused tests use two isolated processes at most.
- Observability: typed errors and existing JSON/exit-status contract; unsupported frozen SHA-256 governance handoff is explicit.

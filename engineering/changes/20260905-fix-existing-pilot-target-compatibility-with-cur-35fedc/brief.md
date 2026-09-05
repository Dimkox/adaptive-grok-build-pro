# Fix existing pilot target compatibility with current landing main fde60e040167c10975b00d11f578c4da6763069a and published v2.0.15: preserve analytics and privacy behavior, validate coherent deterministic deployment ZIP and checksum, retaining existing authorization and confinement. Continue the approved single-operator issue-to-candidate workflow.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260905-fix-existing-pilot-target-compatibility-with-cur-35fedc`
Created: 2026-09-05T22:24:21+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

Fix existing pilot target compatibility with current landing main fde60e040167c10975b00d11f578c4da6763069a and published v2.0.15: preserve analytics and privacy behavior, validate coherent deterministic deployment ZIP and checksum, retaining existing authorization and confinement. Continue the approved single-operator issue-to-candidate workflow.

## Outcome

Unblock one real issue-to-candidate run against the current client landing without
discarding analytics or producing a stale deployment archive. This repair alone
is not L5, a live run, a pull request on the client, or a deployment.

## Scope

### In scope

- Pin the observed target `fde60e040167c10975b00d11f578c4da6763069a`, tree
  `21817e70e079b772e1f3114a80dfc0320d1ada91`; latest source identity to show is 2.0.15.
- Preserve existing analytics scripts, privacy pages, stylesheet and CSP sources;
  the intended CSP change is only the root JSON-LD digest.
- Proposed target scope is the previous eight source/test paths plus
  `dist/therealaidarkfactory.online.zip` and `dist/SHA256SUMS.txt`.
- Archive must contain exactly the 24 existing build-release.ps1 allowlisted
  members, matching source bytes, fixed metadata and matching checksums.
- Use the existing single-run pilot, model and host executables; existing binary
  hashes were rechecked and match the published operator runbook.

### Out of scope

- New subscription, paid API fallback, production deployment, Ads mutations,
  changes to client analytics/privacy behavior, trust policy/keys/holdouts,
  unrelated old PRs, or generic multi-provider orchestration.

## Constraints

- Backward compatibility: supersede only the stale landing target epoch; keep
  the published 2.0.15 archive immutable and preserve existing factory components.
- Data/privacy: no credentials or customer data read/copied; host-owned auth only.
- Performance: affected tests only; no rerun of passing unrelated root/Postgres
  suites. One bounded provider attempt after its actual prerequisites are met.
- Operational: the route's scope-and-design gate is awaiting explicit approval
  of the ten target paths. No implementation or model invocation has started.

## Five sequential handoffs

1. **Current target compatibility.** Input: exact target above, published release
   identity and approved path scope. Output: reviewed profile/semantic repair,
   exact control SHA and profile digest; unaffected client bytes preserved.
2. **Real execution.** Input: that frozen profile, refreshed issue snapshot,
   existing host login and bounded invocation authority. Output: one real model
   outcome and sealed candidate SHA, or a preserved concrete terminal failure.
3. **Candidate acceptance.** Input: sealed candidate. Output: one configured
   target test result plus independent semantic/archive verdict bound to its SHA.
4. **Client proposal.** Input: passing candidate and exact delegated operations.
   Output: non-force target branch and draft PR URL with matching head SHA.
5. **External acceptance / operation.** Input: that exact PR. Output: separately
   observed external CI and human acceptance; deployment only with named target,
   recovery evidence and explicit authority. Missing client Trust CI setup is
   not replaced by local receipts. Do not claim L5 from one successful pilot.

## Evidence already observed

- Remote fetch advanced the target from 80d6215 to fde60e0; subsequent changes
  were five research/design documents, while analytics landed earlier in 80d6215.
- `tests/test_landing.py` requires every ZIP member to equal its source file.
- ZIP is currently 193089 bytes, comfortably inside the pilot diff limit.
- The existing semantic CSP map still describes the pre-analytics policy, and
  the runtime publication authority is pinned to the previous implementation
  route. Both must be considered explicitly; changing the SHA alone is insufficient.
- The existing semantic evaluator incorrectly reads JSON-LD root `version`;
  the actual client document has one `SoftwareSourceCode` inside `@graph`.
- A fresh private no-local/no-hardlinks source is prepared at
  `/tmp/agbp-landing-source-20260905.SFzYp2/source`, exact fde60e0/tree21817e70,
  clean, owner-only 0700 and no remote. The original client checkout is untouched.
- `pwsh` is absent on this host. Do not assume the existing PowerShell packager
  can execute; preserve its explicit inventory and deterministic archive contract
  using the worker's available Python runtime, without adding a dependency.
- Unrelated PR #28 repair was committed/pushed as ef7c8fa; its fresh App check is
  in progress, GitGuardian passed. The sole repeated local test passed (1 method).

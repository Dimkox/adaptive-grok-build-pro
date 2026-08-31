# Security review — M3 restack on accepted M2

## Verdict

**PASS** — no blocking, high, medium, or low security finding remains in the
reviewed merge commit.

- Route: `41eadaeae674`
- Reviewed exact HEAD: `9e9cfbd6971dacd5772d3802d0b758a0c0c5ba83`
- Reviewed Git tree: `3c61ddb9410625050c973256ac5620d6b802af6f`
- First parent (preserved M3): `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`
- Second parent (accepted M2): `022411b05924618cfde0cb97b8c8aff4955e6013`
- Scope: read-only inspection of the committed merge tree and focused tests
  extracted from that exact commit; no credential, `.env`, private-key, external
  service, or production state was accessed.

## Prioritized findings

No findings.

## Trust-boundary review

### Deployed policy, holdout, approvals, and merge authority

The M3 delta from accepted M2 does not modify `trust-ci/`, the holdout bundle,
approval tooling, GitHub Actions, branch protection, or any deployed Trust-CI
control. Repository prose continues to describe local verification, change
packages, and reviews as preflight evidence only. Release instructions still
require a separately authorized PR operation, the App-owned policy-epoch Check
Run on the resulting exact SHA, and every externally signed scope required by
deployed policy.

No repository record is treated as a human private key or as a substitute for
external merge authority. A scan of the changed paths found only test/example
secret values and documentation references; no private-key block, access token,
credential, or production secret was introduced.

### M2 Trust-CI containment and read-only packaging

The following security-critical files are byte-identical to accepted M2 when
compared with `022411b05924618cfde0cb97b8c8aff4955e6013`:

- `trust-ci/src/adaptive_trust_ci/workspace.py`
- `trust-ci/tests/test_workspace.py`
- `scripts/package_stack.py`
- `.grok-stack/adaptive_grok/manifest.py`
- `.grok-stack/adaptive_grok/architecture_diff.py`

The merge therefore preserves descriptor/source-invariance packaging controls,
command-scoped Git trust, and bounded post-SIGKILL classification. The process
classifier remains fail closed for live or uncertain groups and preserves an
original bounded command failure only for a proven all-zombie group.

### M3 governance authority and provenance

Governance registries remain empty; the merge does not activate a rule, example,
or debt record. Canonical JSON remains authoritative while Markdown projections
are explicitly non-authoritative.

Loaded rule effects are bound to loader-created repository identity and live
evidence; caller-reconstructed or rebound records do not inherit authority.
Promotion fitness adds an unconditional external exact-record authority finding
for a newly active rule, and active examples or terminal debt claims likewise
remain hard-gated by external-authority findings. Repository-authored actor names,
timestamps, and approval-looking fields therefore cannot by themselves make a
new promotion pass the architecture gate.

Governance handoff generation requires a clean exact Git state, matches the
requested head, compares every consumed governance input with the corresponding
blob at that head, independently rederives M2 architecture evidence, and rejects
stale or self-hashed substitutes. The active route and merge topology both bind
accepted M2 exactly; `git merge-base --is-ancestor 022411b... 9e9cfbd...`
succeeded and the two recorded parents match the intended order.

### Conflict resolution

The remerge diff contains no policy/holdout/approval conflict. Append-only
security and provenance lessons from both parents were retained. The test
conflicts remove only branch-history-dependent assertions that M2 had not changed
`trust-ci/`; governance-promotion and exact-base assertions remain. The finite
architecture budget remains exactly `10820`, and mandatory governance handoff /
promotion fitness remains configured.

## Verification evidence

Ten focused tests passed from a clean archive of exact commit `9e9cfbd...`:

- caller rebinding and equal-content cloning do not acquire governance authority;
- swap/restore governance inputs cannot produce an exact-head handoff;
- external-authority findings remain a hard handoff gate;
- agent or projection-only rule promotion fails governance fitness;
- zombie-only classification succeeds while live/uncertain post-kill state fails
  closed and preserves only the permitted original error.

Result: `Ran 10 tests in 1.487s — OK`.

## Residual risk and validity

This report is local review evidence, not merge authority. PR #11 still needs a
fresh App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run and every
required signed scope on its exact delivered head. This PASS applies only to
commit `9e9cfbd6971dacd5772d3802d0b758a0c0c5ba83`; any subsequent product-tree
change invalidates it and requires verification plus a new independent security
review.

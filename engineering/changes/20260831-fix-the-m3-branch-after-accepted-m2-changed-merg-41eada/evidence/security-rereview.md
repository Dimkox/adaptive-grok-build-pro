# Security rereview — CR-001 remediation

## Verdict

**PASS** — CR-001 was repaired without weakening a security or trust boundary.
No blocking, high, medium, or low security finding remains in this rereview.

- Route: `41eadaeae674`
- Reviewed exact HEAD: `f998ed28efd928ae0627a9e690029bb75e4264db`
- Reviewed Git tree: `7653f5fa3175552bff04f3233d3366fa50fd17d0`
- First parent (preserved M3): `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`
- Second parent / exact accepted M2 base:
  `022411b05924618cfde0cb97b8c8aff4955e6013`
- Prior report: `evidence/security-review.md` remains historical evidence for
  superseded HEAD `9e9cfbd6971dacd5772d3802d0b758a0c0c5ba83` and was not reused.

## Prioritized findings

No findings.

## CR-001 remediation

The only executable-tree delta from `9e9cfbd...` is removal of two assertions
from `tests/test_change_receipts.py`. Both assertions coupled receipt tests to
the incidental whole-history architecture result. Their removal restores the
accepted-M2 branch-independent contract while retaining assertions for:

- the architecture check identity and configured state;
- the frozen adoption comparison base;
- the independently selected route base;
- architecture fingerprint and evidence linkage;
- receipt staleness and M3 governance binding.

No production implementation, schema, contract, policy, configuration, runtime,
or external adapter changed. The remaining additions are review/remediation
reports that explicitly identify themselves as local evidence and do not claim
merge authority.

## Preserved trust boundaries

### Trust CI, holdout, approvals, and secrets

The remediation changes no `trust-ci/` source, holdout content, approval tool,
policy, image, trust store, branch-protection configuration, or GitHub Actions
workflow. It performs no external or production write and introduces no secret,
credential, token, or private-key material.

The App-owned policy-epoch Check Run on the final PR SHA and every independently
signed scope required by deployed policy remain mandatory. Neither the merge,
the local verifier, nor any report in this commit substitutes for them.

### M2 containment and read-only packaging

The following paths remain byte-identical both to the pre-remediation merge and
to exact accepted M2:

- `trust-ci/src/adaptive_trust_ci/workspace.py`
- `trust-ci/tests/test_workspace.py`
- `scripts/package_stack.py`
- `.grok-stack/adaptive_grok/manifest.py`

Thus descriptor/source-invariance packaging, command-scoped Git trust, bounded
TERM/KILL handling, zombie-only acceptance, and live/unknown fail-closed process
classification are unchanged.

### M3 governance authority and exact-state provenance

The governance engine, promotion fitness, frozen schemas, and empty canonical
registries are byte-identical to the prior reviewed merge. Loader-created
repository provenance, live evidence validation, external exact-record promotion
findings, clean exact-Git handoff generation, consumed-blob comparison, and
independent architecture rederivation are preserved.

Exact accepted M2 remains the merge's second parent and an ancestor of HEAD. The
finite architecture budget remains `10820`, and
`FIT-GOVERNANCE-HANDOFF-COMPATIBILITY` remains configured. No historical receipt
or handoff is promoted to current authority.

## Verification evidence

Seven focused tests passed in an isolated clone checked out detached at exact
HEAD `f998ed28...`:

- both remediated receipt/base-binding tests;
- caller rebinding cannot acquire governance authority;
- swap/restore authority bytes cannot produce an exact-head handoff;
- agent promotion fails governance fitness;
- live and uncertain post-kill process groups fail closed.

Result: `Ran 7 tests in 21.570s — OK`.

Static diff inspection also confirmed that the remediation delta contains only
the two test-line removals plus evidence reports, and that no policy, holdout,
approval, secret, or external-write path appears in the changed-file set.

## Residual risk and validity

This is local security-review evidence for exact commit
`f998ed28efd928ae0627a9e690029bb75e4264db`, not merge authority. Any later
product-tree change invalidates this PASS. PR #11 still requires fresh
fingerprint-bound verification/reviews and the App-owned policy-epoch check plus
all required signed scopes on its final delivered SHA.

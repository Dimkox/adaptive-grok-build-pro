# docs_researcher — M0.0 “laptop” inventory (read-only)

Route `c8e5e567a15d`. User fact: agent workspace is host `claw` (Xeon 4xxx, 16 GiB ECC), not a laptop. Implementer must replace **this laptop** / **laptop** with **host `claw`**. Do not invent APIs.

## In-scope files

| File | Hits |
| --- | --- |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | 3 |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | 1 |
| `engineering/runbooks/trust-ci-activation-report.md` | 0 |
| `trust-ci/tests/test_m0_invariants.py` | 0 |
| PR #5 body in this change package | absent |

## Exact replacements (spec)

L42: `this laptop` → `host \`claw\`` in Untrusted list.
L62: `This laptop is **forbidden** as the Trust CI host` → `Host \`claw\` is **forbidden** as the Trust CI host` (keep SearXNG/8080/DinD/HTTPS reasons).
L109: `Using this laptop as the CI host` → `Using host \`claw\` as the CI host`.

## Exact replacement (plan)

L22: `(not this laptop)` → `(not host \`claw\`)`. Host name for dedicated CI remains required separately; `claw` is the **disqualified** workspace host, not the CI target.

## Out of this slice

Activation report and `test_m0_invariants.py` have no `laptop` string. PR #5 body is not stored under this package; do not guess GH text.

Do not retarget Trust CI onto `claw`; only correct the misnomer.

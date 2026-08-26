# Test plan — Model Agnostic Autonomous Factory

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Typed package is red-risk, complete, schema-valid, evidence-mapped, and placeholder-free | `grok_spec validate`, map output, placeholder scan |
| P0 | Design contains all approved hard limits and no silent fallback/external-write/CoT loophole | self-review report and source scans |
| P0 | Canonical design and package agree on milestone order and trust separation | contradiction review |
| P0 | No implementation code, plan, external action, systemd install, or second package exists | diff/status/scope review |
| P1 | Markdown formatting, links, and repository structure remain valid | `git diff --check`, focused structure tests, PR-mode local verification |

## Automated checks

- Unit: existing M1 typed-spec tests remain green; this gate adds no runtime unit.
- Integration: no factory integration exists or is claimed at the design gate.
- Contract: validate `change-spec.yaml`; inspect protocol and exact-state design invariants against all analysis reports.
- E2E: not applicable before M4-M6 implementation; later gates require PostgreSQL, process-kill, adapter, isolation, and semantic-repair evidence listed in the canonical design.
- Static analysis: placeholder/scope/security scans, `git diff --check`, and repository quality profile.

## Manual checks

- Verify branch and changed-file set before commit.
- Confirm five analysis reports and design self-review exist.
- Confirm no credential, secret, or raw reasoning entered the design.
- Confirm state remains `scoped` and awaits explicit user approval.

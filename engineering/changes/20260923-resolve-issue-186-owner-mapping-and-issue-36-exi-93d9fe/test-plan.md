# Test plan — Resolve issue #186 owner mapping and issue #36 exit-status disposition

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Characterization/source audit at exact SHA finds no owner and records commands/source identity | `evidence/owner-mapping.md` |
| P1 | Existing Python/Trust CI result paths preserve nonzero exit codes | Four analysis reports; no product test added for absent code |

## Automated checks

- Unit: not applicable; no product behavior changed.
- Integration: not applicable; no integration changed.
- Contract: no OpenAPI/events/SQL/Trust CI contract changed.
- E2E: not applicable; no owner exists.
- Static analysis: `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- Manual: review exact SHA, commands, source paths, mappings, and explicit no-closure blocker in owner-mapping.md.

# Test plan — Implement repository custody for already-built deterministic v2.1.0 package bytes from source e5856acfd4bc7a186f40a740b54ec86459462db5: add ZIP and checksum, update candidate state documentation and binding tests without publication or activation

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Artifact hashes and source identity bind exactly | project-state and manifest-package tests |
| P1 | Published v2.0.19 and activation state remain unchanged | project-state tests |

## Automated checks

- Unit: project-state bindings.
- Integration: structure/state/manifest lockstep.
- Contract: change-spec gate.
- E2E: not run; no delivery action.
- Static analysis: diff check.

## Manual checks

- Confirm ZIP and sidecar hashes with `sha256sum`.

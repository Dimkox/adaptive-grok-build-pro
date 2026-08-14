---
name: bugfix-workflow
description: Use for defects, regressions, exceptions, and hotfixes. Requires reproduction, root-cause evidence, a failing regression test, minimal repair, and verification.
---

# Bugfix Workflow

1. Reproduce the failure or establish a deterministic evidence trail.
2. Trace backward from the failing value or behavior to the first incorrect state.
3. Distinguish root cause from symptoms and incidental cleanup.
4. Add a failing regression or characterization test.
5. Apply the smallest defensible fix through the route's single write owner.
6. Verify the original reproduction and nearby failure paths.
7. Review for regression risk and operational impact.

For production incidents, preserve logs and evidence before cleanup. Do not bundle unrelated refactoring into the fix.

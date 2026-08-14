---
name: legacy-modernization
description: Use for refactoring or replacing legacy code while preserving behavior and controlling architecture debt.
---

# Legacy Modernization

1. Map dependencies and runtime behavior.
2. Add characterization tests around the seam.
3. Define the stable compatibility contract.
4. Introduce a bounded adapter or seam.
5. Migrate incrementally with old/new comparison where possible.
6. Record temporary debt and removal criteria.
7. Delete old code only after evidence proves compatibility.

Do not respond to a tangled monolith by creating unbounded microservices. Improve the boundary required by the current outcome.

# Evidence index

- `analysis-*.md`: route-selected analysis conclusions, reduced to transferable requirements; source-specific findings are private.
- `implementation.md`: synthetic test-first implementation and focused checks.
- `factory-preflight-repair.md`: reproduced mixed-clock fixture defect and two-line repair.
- `private-reconciliation.md`: sanitized method and accounting reconciliation; detailed artifacts remain outside the checkout.
- `verification-matrix.md`: actual initial full-preflight results and successful corrected disposable factory component.
- `code-review.md`, `test-review.md`, `security-review.md`: independent final PASS reports. Their source bindings remain unchanged by workflow-document finalization.

Machine receipts live under `.grok-stack/runtime/receipts/78b680187560/` and are bound only after the final candidate commit and full verification. Read `python3 scripts/grok_status.py` for current evidence gaps. Reports and local receipts never grant merge or external operation authority.

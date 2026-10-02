# Rollback plan — Implement bounded Factory v1.5 result admission contract API

## Trigger conditions

V1 regression, contract/runtime mismatch, unintended store access, or any response implying durable success.

## Application rollback

Revert this isolated slice; V1 and PR3a behavior remain the fallback.

## Data recovery / forward-fix

No data recovery: this slice performs no writes. Repair contract/API logic and rerun full gates.

## Verification after rollback

Run broker/result schema/API/architecture suites and full PR verification.

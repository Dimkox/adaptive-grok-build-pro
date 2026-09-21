# Docs researcher analysis — issue #162

## Established contract and gap

`schemas/change-spec.schema.json` is the v2 typed specification. Its `$defs.evidence.properties.receipt.enum` currently admits five values and omits `bitrix_review` and `data_review`. Both `.grok-stack/adaptive_grok/receipts.py:42` and `workflow_artifacts.py:36` define seven kinds; `router.py:405-417` can require the omitted two. The issue's parity claim is confirmed by source. `tests/test_workflow_artifacts.py:798-803` compares the two runtime sets and checks the domain kinds, while `tests/test_change_spec.py:362-367` checks schema metadata only. Thus no test catches schema/runtime drift.

## Acceptance criteria and useful controls

1. A new parity assertion should compare the schema enum as a **set** to the canonical runtime receipt set; the existing runtime-to-runtime assertion remains. The seven current kinds should all validate in a minimal otherwise-valid v2 spec, and an invented receipt kind should still fail with the enum error. This proves both inclusion and closure, not merely a two-entry addition.
2. Preserve the receipt evidence object's single-key shape and route/binding semantics. `receipts.py:483-493` loads and validates the active spec before mapping criteria to a receipt kind; broadening the enum must not admit arbitrary string values or create receipt authority.
3. The proposed early scaffold validation is secondary. `scripts/grok_change.py` is a thin CLI wrapper; `adaptive_grok/change.py:start_change` calls `generate_spec()` and writes it, but does not validate it. Adding a gate there could widen this bounded schema fix and risks validating placeholder content under gate-only rules. First prove the schema parity regression; assess early validation separately if a generated spec is demonstrably invalid after the enum fix.

Focused test home: `tests/test_change_spec.py`, with existing parity in `tests/test_workflow_artifacts.py`. No database or external service is needed. This is analysis only; no tests or product code were run or changed.

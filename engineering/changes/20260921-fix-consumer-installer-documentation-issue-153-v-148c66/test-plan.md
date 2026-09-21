# Verification plan

Status: focused implementation checks passed; full PR verification and independent review remain with the coordinator. Exact red/green evidence and limits: [implementation report](evidence/implementation-general_implementer.md).

After the first independent reviews requested changes, the corrected focused suite passed 33 tests. Its new contract covers explicit installed `.md.tmpl` artifacts and installed-consumer source reproduction. The source-relocation fixture now succeeds unrelocated and asserts the specific directory-binding refusal after relocation. First-review failures remain historical evidence; fresh full verification and independent re-review must bind the corrected product hashes.

Add failing installed-tree link and mandatory-file checks before changes; include one valid/one broken link checker control. Cover generic/Bitrix rendering, helper/payload parity, manifest hashes, emitted safety wording and exact preservation of existing AGENTS user text. Test kept_local conflict and existing-target materialize refusal.

Focused: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_installer.py'. Run test_verification_doctor.py only if changed. Record actual red/green logs; no live consumer/network is required.

Coordinator runs python3 scripts/grok_verify.py --mode pr on the final tree, then dispatches code_reviewer and test_reviewer. Record actual reports and fingerprint-bound receipts under their existing exact kinds; do not relabel reviews. Schema-v2 references use verification/code_review/test_review only. Full local preflight never substitutes for the App-owned exact-PR-head Trust CI check.

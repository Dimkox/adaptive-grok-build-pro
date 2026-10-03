# Verifier lifecycle recovery (contour A)

Typed authority: [change-spec.yaml](change-spec.yaml). Route c2333ca04e25; sole writer general_implementer; initial base e5856acfd4bc7a186f40a740b54ec86459462db5. User approved the full 2.1.1 recovery design on October 1; this package implements its section A and does not change VERSION or release state.

The previous runner discarded a completed result when its signal context raised on exit. The verifier called receipt binding/publication after constructing its report without containing exceptions, so a secondary error could hide the test verdict. Receipt replacement fsynced the file but did not ensure directory durability or explicitly retire an old pass on failure.

In scope: owned runner lifecycle; incremental verifier check retention; cancellation envelopes; receipt/report finalization; receipt HEAD binding and atomic durable publication; fresh negative controls. Expected product files: python_test_runner.py, verification.py, receipts.py, grok_verify.py, and tests/test_verifier_recovery.py.

The structured report keeps check_status separately from final status, terminal_state and evidence_status. Tests that completed remain visible; publication errors fail the gate. Signal cancellation carries its original code and report, terminates only the invocation-owned process group, and makes one terminal receipt attempt. D owns input/architecture preflight and will be integrated independently into _verification_run; record=False leaves evidence_status=not_recorded.

Historical cancel and verification-recovery trees were read-only design inputs. Only issue-226 commits dde3a2601c5b68d3da1b26e2434ba00b9ba83007 and 01b14df68f39feffa93e23b285f8f1825719850a were inspected for that delta; no commits, archived packages or evidence were imported. Issue 227 and its grant-boundary changes are excluded. The scope selector, modes, factory inventory, deployed policy, approvals and external merge authority remain outside this implementation.

Delivery is a scoped commit followed by merge of actual origin/main 63799f8760d3a55028d83ab5ff0116ececf8f7d1 as instructed by the controller. Focused checks are implementation evidence. Full verification, independent reviews, push/PR and external Trust CI remain controller-owned.

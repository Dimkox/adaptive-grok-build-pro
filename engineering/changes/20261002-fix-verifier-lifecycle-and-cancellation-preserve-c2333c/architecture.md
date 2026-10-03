# Recovery boundaries

Typed authority: [change-spec.yaml](change-spec.yaml).

python_test_runner owns each Popen's new process session, bounded output files and cancellation token. The main-thread token installs/restores SIGTERM and SIGINT handlers, preserves the first signal, and is shared by nested verifier commands. Cleanup sends TERM, waits at most 0.25 seconds, then sends KILL and reaps with two bounded 2-second waits. Completed exit codes survive cleanup errors; cleanup_error separately fails consumers' gate status.

verification runs commands through that ownership boundary and accumulates checks before later stages. RunCancelled carries the latest process result; partial Python, Core coverage, composer and npm checks survive unwinding. verify is the cancellation/report envelope; _verification_run contains the current selection and check dispatch. D's independent preflight belongs there and can set record=False without losing its failure.

Finalization freezes check_status before receipt recording. status is the final local gate outcome, terminal_state distinguishes completed/cancelled, and evidence_status distinguishes recorded/not_recorded/failed. VerificationCancelled carries the structured report and signal exit. A cancellation during receipt publication is followed by exactly one terminal-failure publication attempt; repeated signals are deferred and idempotent while recovery runs.

receipts retains existing spec/architecture/governance bindings and adds optional git_head. The current head is compared before and after binding construction and when validating new receipts. Same-directory temporary publication fsyncs bytes, replaces atomically and fsyncs the directory. Tested faults remove temporary data and invalidate old/fresh pass bytes. Legacy envelopes without git_head remain readable.

grok_verify preserves structured output for signal exits. If stdout publication fails, it attempts the retained JSON report on stderr and records failed publication evidence when recording is requested. If both output channels fail, the process still exits nonzero. Cancellation during report output preserves the completed verdict and publishes failed terminal evidence.

No service, database, framework or dependency is introduced. Local evidence APIs remain compatible through additive fields and optional parameters. The deployed Trust CI policy, holdout, human approvals and branch protection are untouched and retain all merge authority.

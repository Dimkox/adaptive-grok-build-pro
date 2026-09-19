# Documentation research — cancelled verification attempts (#119)

## Finding

The existing CLI is intentionally a stdout/exit-status interface: `scripts/grok_verify.py` prints either the complete verifier report (`--json`) or a compact per-check summary, then exits 0 only for `pass` and 1 for every other returned status. It does not promise a persistent report file. `verify()` in `.grok-stack/adaptive_grok/verification.py` returns a `schema_version: 1` report whose `status` is currently `pass|fail`; it records a verification receipt only after normal completion when the route exists, governance did not fail, and the source fingerprint remained stable. The report's own explanatory validator, `summarize_verification_report()`, is a separate bounded sample-evidence format (`status: sample_evidence`) and should not be stretched into the runtime report contract.

The receipt envelope is deliberately stricter: `receipts.py::validate_evidence()` accepts only receipt status `pass|fail`, and only `pass` closes a required-evidence gap. Therefore cancellation should be represented as a distinct **report outcome** (or a check/outcome detail) while leaving the receipt status enum unchanged; a cancelled attempt must not write a passing verification receipt. If a stale prior receipt exists, its invalidation behavior is a lifecycle concern and should be covered in implementation/tests, not explained as a new public receipt status.

## User-facing documentation impact

No README, hook, or CLI usage guide currently documents a persistent verification-report schema or an interrupt/cancellation outcome. The CLI help only describes route-selected verification and fingerprint-bound receipt recording. The Stop hook is explicitly warning-only and reports missing/stale evidence; it neither consumes verification reports nor needs a cancellation-specific branch (`.grok/hooks/README.md`, `stop_gate.py`). The existing CLI output contract is enough for this bounded fix if the implementation prints/returns a clear cancellation status and preserves a nonzero exit. Add a concise `grok_verify.py` help/README note only if the implementation adds a persistent report artifact or materially changes `--json` fields; otherwise a new user-facing doc section would duplicate the command's self-evident output and risks implying a stable report-file API that does not exist.

## Evidence reviewed

- `scripts/grok_verify.py`: stdout JSON/text and exit code are derived from `report['status']`; no report path option.
- `.grok-stack/adaptive_grok/verification.py::verify`: report assembled after checks; receipt write occurs only on normal return and stable source.
- `.grok-stack/adaptive_grok/receipts.py::validate_evidence`: closed receipt status set is `pass|fail`; only `pass` satisfies evidence.
- `.grok-stack/adaptive_grok/verification.py::summarize_verification_report`: separate sample-only format, not the runtime report schema.
- `.grok/hooks/README.md` and `.grok/hooks/stop_gate.py`: Stop behavior is warning-only and keyed to receipt gaps.
- README describes `grok_verify` as local verification/receipt tooling but documents no durable report-file contract.

**Recommendation:** keep `cancelled` distinct at the runtime report/CLI layer, never permit it to satisfy receipt validation, and do not introduce broader documentation unless a report artifact or user-visible option is added.

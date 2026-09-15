# Test plan — Workflow Artifact Adapters

P0: authority escalation, command injection, path/symlink/special-file races, duplicate/ambiguous/deep JSON, YAML authority syntax, structural/schema parity limits, no compiler process/network/LLM, canonical receipt forgery/symlink/FIFO checks, descriptor-safe CLI authority reads, serialized CAS special-entry/double-race recovery, source/effective status separation, native source-status drift, cycles/write conflicts/exact coverage, and source mutation. Evidence: `tests/test_workflow_artifacts.py`, `tests/test_workflow_artifacts_cli.py`, and `tests/test_workflow_artifacts_adversarial.py`.

P1: happy-path mappings for all three adapters, deterministic identities/task graphs/reports/exports, placeholders/conflicts/status drift, historical verifier skip, installer/package inventory and read-only source packaging. Evidence: focused workflow tests plus verifier/installer/manifest tests.

Final: `python3 -m unittest discover -s tests -v`; `python3 scripts/grok_verify.py --mode pr`; route-selected code, test, security, and release reviews on one final fingerprint.

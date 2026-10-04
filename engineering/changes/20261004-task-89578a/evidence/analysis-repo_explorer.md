# Repo explorer — read-only analysis

Source HEAD ee3911869419204154e02900e58bf31492ee744c. Resource snapshot recorded privately at .review-scratch/resource-fast-explorer-20261004T195617Z.md; verified28 CPUs, one lightweight worker. No candidate edits or full suites.

Deterministic bounded reproduction: _python(...,'pr') still runs pilot, Core, Factory unit and PostgreSQL after injected ruff=fail; Factory also runs after python-unittest=fail. No real suite/subprocess check ran.

Insertion points: verification.py:2161 repository dispatch; earlier spec/architecture/governance/workflow functions2107–2156 precede accumulation and need boundaries too. _python_checks:1743 needs refusal handling after lint/security/pilot/discovery/Factory; _focused_python:1706 also continues into Factory. Composer1529 and Node1641 internally run complete batches. run_core_tests:524–553 continues coverage export after failed tests.

Retain primary output, disclose scheduled work not executed, aggregateFAIL/nonzero, unchanged scope, source-stability and binding finalization. Do not evaluate full QG on an incomplete prefix: quality_gates.py:105–139 rejects future missing mandatory names. Share per-result policy; final QG remains complete.

Architecture preflight2131 refuses receipts; governance/stability2253 also preserve binding refusal (tests/test_verification_doctor.py:1068/1122). tests/test_python_test_runner.py:494–507 pins non-null failed coverage; coverage=None would need explicit compatibility handling. Direct fast _python callers and allowed skips remain compatible.

Targeted controls: repository refusal prevents Python but retains valid FAIL receipt; ruff blocks pilot/Core/Factory; failed discovery blocks Factory; failed Factory blocks PostgreSQL; failed focused discovery blocks Factory; allowed skips/success order unchanged; cancellation/refusal intact. Controller ruling preserves integrated coverage contracts and optimizes PR/release.

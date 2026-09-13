# Architecture

Follow evidence/split-de-integration.md and evidence/split-d-data-analysis.md. Introduce helper-only landing_host_config, six actual modules and 19-member inventory; host boundary contains landing_server only. Keep public API unchanged and defer dedicated host, publication, backup and the cross-feature Qwen test tail. HTTP parser/DTO module remains offline; only live executors may perform provider I/O. SQL schema, migrations and existing durable readers remain unchanged.

The delivered SQLite file has one disclosed corrective deviation from frozen source: three cleanup hunks cover connect/configure interruption, close failure during unwind, and interruption after flock. Failure-injection RED/GREEN evidence and the exact patch are retained alongside the 24-path manifest. The added test_landing_server.py is an independent D regression module; preserve it and its exact LOCAL-API owner through G.

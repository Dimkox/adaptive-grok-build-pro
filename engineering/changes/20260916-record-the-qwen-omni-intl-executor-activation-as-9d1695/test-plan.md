# Test plan

`python3 -m unittest tests.test_project_state` (three-service loop incl. omni model equality), `tests.test_structure`, `tests.test_manifest_package`, `tests.test_change_spec`; then full `grok_verify --mode pr`. Activation truth itself is externally observable (unit active, socket 200, provider normalized) and cited, not asserted by unit tests.

# Dependencies and owners

- Completed: CPU measurement, route6af9e6eed1d8, four read-only analyses.
- Application-code writer: cleanup_general_implementer.
- Static/targeted checks after implementation; combined heavy workers capped at measured28.
- Historical full PR attempt is preserved with its failures; repair affected checks before repeating it.
- Parallel code/test reviews use private scratch and return reports out-of-band. Persist final reports before the one final full PR verification.
- Final verification uses 12 core-test workers within measured 28-CPU capacity; PostgreSQL exit remains selected. No extra full run for report-only paperwork.
- Exact delegated branch push; App-owned Trust CI on new SHA; merge after external gates.

# Test plan

`python3 -m unittest tests.test_project_state` (three-service loop incl. omni model equality), `tests.test_structure`, `tests.test_manifest_package`, `tests.test_change_spec`; then full `grok_verify --mode pr`. Activation truth itself is externally observable (unit active, socket 200, provider normalized) and cited, not asserted by unit tests.

What the record loop actually pins, after rounds 3 and 4 (disclosed because "asserted" and "cited" are
not the same claim, and because these assertions read the **checked-in** capture rather than the host):

- each service's `ActiveState`/`UnitFileState`/boot timestamp against **its own** block of the verbatim
  systemctl capture, matched on the `ActiveEnterTimestamp` property name — so a stamp borrowed from
  another unit or from `ExecMainStartTimestamp` fails;
- `runtime_observations.observed_at` equal to the dossier's `observed_at`;
- the omni identity leaves (`unit`, `selected_profile`, `model`, `installed_sha`, `live_enabled`) equal
  between state and dossier, and every acceptance leaf equal to the dossier's `activation` block
  (health capture excepted), with the probe job kept distinct from the pilot job;
- the pilot block against its `db_row` corroboration (job, state, revision 3, completion instant
  `2026-09-17T00:21:16.151094Z`, usage 813/364), including `updated_at[:19] < observed_at[:19]`.

Not asserted: that the units are *still* in the recorded state. No test shells out to `systemctl` or the
sockets, so a later restart or a re-capture makes the record stale silently — the assertions are
state↔evidence agreement, and the next re-capture must edit the capture and all three state stamps in
lockstep (the `Z`-suffix check makes that spelling explicit, since the sibling
`acceptance_observed_at` uses `+00:00`).

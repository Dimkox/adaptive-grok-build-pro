# Test plan

`python3 -m unittest tests.test_project_state` (the record loop: model equality plus the per-unit capture, identity and literal pins enumerated below), `tests.test_structure`, `tests.test_manifest_package`, `tests.test_change_spec`; then full `grok_verify --mode pr`. Activation truth itself is externally observable (unit active, socket 200, provider normalized) and cited, not asserted by unit tests.

What the record loop actually pins, after rounds 3, 4 and 6 (disclosed because "asserted" and "cited"
are not the same claim, and because these assertions read the **checked-in** capture rather than the
host):

- each service's `ActiveState`/`UnitFileState`/boot timestamp against **its own** block of the verbatim
  systemctl capture, matched on the `ActiveEnterTimestamp` property name — so a stamp borrowed from
  another unit or from `ExecMainStartTimestamp` fails;
- `runtime_observations.observed_at` equal to the dossier's `observed_at` and to the top-level
  `observed_at`, and not earlier than the omni boot stamp, the pilot row's completion or the pilot
  observation time;
- the omni identity leaves (`unit`, `selected_profile`, `model`, `installed_sha`, `live_enabled`) equal
  between state and dossier, **and** pinned to literals: `qwen-omni-intl`, and `installed_sha` equal to
  both `observed_main_sha` and the dossier's `source_base`;
- every `acceptance` leaf equal to the dossier's `activation` block (health capture excepted), the probe
  job kept distinct from the pilot job, and the probe's `state` checked against the shipped observation
  vocabulary (`landing_observation.CATEGORIES`) and pinned to the one value actually recorded
  (`normalized`), with `live_url` null;
- the pilot block against its `db_row` corroboration (job, `state` pinned as the literal
  `artifact_ready` rather than only as pair agreement, revision 3, completion instant
  `2026-09-17T00:21:16.151094Z`, usage 813/364), including `updated_at[:19] < observed_at[:19]`.

Measured at this head, one mutant per git-ful `/tmp` copy, with a green control: relabelling the profile
to mainland in **both** files, zeroing `installed_sha` in both, flipping `pilot.state` and
`db_row.state` together, and setting the probe state to `normalizing`, `succeeded` or `Normalized` in
both files are all KILLED. The method also runs in isolation now (the `factory/src` bootstrap moved to
module scope), where it previously needed another test to have run first.

Not asserted: that the units are *still* in the recorded state, nor **when** inside the pinned day the
capture was taken. No test shells out to `systemctl`, `journalctl` or the sockets, so a later restart
makes the record stale silently. The ordering asserts do bite — moving all three observation stamps to
`2026-09-17T00:00:00Z`, earlier than the pilot row's `00:21:16Z` completion, is KILLED — but a
consistent move to any time at or after every pinned fact (`00:30:23Z`, `09:00:00Z`) stays green, and no
in-tree assertion can do better, because nothing in the tree records the wall clock of the capture.
Crossing the day in either direction is caught (`2026-09-18T09:00:00Z` fails the date pin). The next
re-capture must therefore edit the capture and all three state stamps in lockstep (the `Z`-suffix check
makes that spelling explicit, since the sibling `acceptance_observed_at` uses `+00:00`).

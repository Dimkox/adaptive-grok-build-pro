# Requirements — v2.0.18 release sync (R)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

1. `AC-001` — one coherent candidate identity across VERSION, README, CHANGELOG, START_HERE, ROADMAP, HANDOFF, `adaptive_grok.__version__` and `PROJECT_STATE.product_version`, with `published_release`/`latest_published_release` unchanged at v2.0.17.
2. `AC-002` — landing rows for #101/#102/#105/#106 re-derived from Git + GitHub checks API (exact heads, merges, times, check-run ids), nothing pre-publication rewritten, chain commits excluded from rows by the convention recorded in #102.
3. `AC-003` — pending `local_candidate` (null identities, artifact pair absent, v2.0.18 delta names) and verbatim archive of the published v2.0.17 candidate record.
4. `AC-004` — bootstrap docs state the post-publication truth including #86's remainder and #104; the new runtime dossier's `source_base` equals the new `observed_main_sha` and its service fields match `runtime_observations`.
5. `INV-001`/`INV-002`, `FORBID-001`/`FORBID-002` per the typed spec.

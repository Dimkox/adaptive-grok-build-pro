# Residual risks after three independent reviews

What this change does not fix, each with the measurement or the citation that establishes it. Nothing here is a
blocking finding for the merge; everything here is a claim a later reader should not have to rediscover.

1. **Issue #147 stays open, deliberately.** The comparator still resolves declared-`$id` before the declared-path
   table, so a contract declaring a path-like `$id` captures references naming that path and a real narrowing of the
   captured target reports `compatible`. Measured latent: 50 declared contracts, 41 `$id` values, none equal to a
   declared path, and 0 references where the two tables disagree. This change keeps that precedence byte-identical
   (`architecture.py:1409`, `SCHEMA_REFERENCE_ID_FIRST`) and only stops the *closure* from inheriting it; the
   differential over 1050 verdict rows is empty.

2. **Issue #148 is created by this change.** The `unattributed reference` signal that replaces the base-side abort is
   appended once per colliding reference and per referrer, with no aggregate cap (only the carrier list inside a
   message is bounded, `_AMBIGUITY_OWNER_LIMIT = 5`), and because the closure walks both inventories the same
   collision is recorded twice; a review measured ~2000 findings ≈ 309 KB from one in-scope referrer. Bounded by
   `MAX_CONTRACTS = 256` and the 1 MB per-document cap, so it bloats reports rather than crashing them.

3. **"One grammar, cannot drift" is true for the closure and not fully true for the comparator.** A reviewer's
   mutation that replaces the shared helper's use inside `resolve()` with a behaviour-equivalent private
   implementation survives all 204 tests, so the guarantee that holds is "one implementation exists and the closure
   calls it", not "the comparator cannot grow a private copy". The closure-side lock is real: `assertIs` on the
   shared fold plus `test_contract_dependency_closure_shares_the_comparator_reference_grammar`.

4. **The structural superset arm cannot catch the C2 class on today's fleet.** It compares the legacy fold against
   the shipped closure over the declared inventory, and **zero** shipped contracts use a declined spelling
   (`./x.json`, a space or `+` in a name), so re-applying the intermediate regression leaves that arm green while the
   three synthetic spelling arms fail. The durable protection for that class is therefore the reason split plus the
   tripwire `test_reference_reasons_keep_declined_paths_apart_from_non_paths`, not a fleet number.

5. **Kind divergence between the two consumers of the grammar.** The comparator refuses a target whose kind is not
   `event`/`json_schema`/`signed_payload`; the closure does not filter by kind, so an `$id` declared on an OpenAPI
   document can produce a reverse edge whose pair verdict later returns `unsupported`. Direction is conservative
   (re-verify more, never less); measured zero instances on the declared inventory.

6. **Union attaching both candidates means double verification, not mis-attribution.** Where a base names both a
   declared path and some contract's `$id`, the referrer is pulled under both targets; findings keep naming the
   edited contract, so the row is attributable. Dropping the `$id` leg reddens two tests, so the second leg is
   load-bearing rather than decorative.

7. **Blast radius in one sentence, with the counting definition.** Three targets gain `M7-READY-BUNDLE-V1` as a
   re-verified dependent; **two** gain a new failure because the third already fails on its own unanalyzable row
   (`closure-fix-blast-radius.md`). Unblocking `M7-READY-BUNDLE-V1` — one of the last two contracts the comparator
   still cannot analyze — removes the entire new-failure surface.

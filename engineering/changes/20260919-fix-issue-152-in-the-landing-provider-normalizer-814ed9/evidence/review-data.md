# Data review — issue 152

**Verdict: PASS. No blocking data findings.**

Role: route-selected `data_reviewer`, independent of the implementation owner. Route: `814ed9c452cd`. Workspace: `/var/tmp/adaptive-issue152-20260919`; branch: `fix/issue-152-draft-diagnostics`. Reviewed the actual uncommitted diff against HEAD/base `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`, the frozen legacy fixture, and surrounding persistence, receipt, API and failover code. Read the repository contract, bootstrap handoff, role instructions, active route, applicable workflow skills and change package.

## Findings and evidence

1. **The existing reason field accommodates the new vocabulary.** `landing_http.py:78–106` emits only 17 constant mapped values or the constant `draft_validation_failed`; the longest value is 25 characters. Malformed/non-string contract codes and non-exact provider exception arguments use the fallback without interpolating details. The unchanged outcome validator accepts bounded identifiers (`landing_provider.py:38,275`), and the attempt schema permits a nullable string of 1–128 characters without a value enum (`factory/contracts/jsonschema/landing-attempt-status.v1.schema.json:43–53`). SQLite already stores `reason_code TEXT` (`landing_sqlite_store.py:46`), so this introduces no new representation or schema change.

2. **The retained digest comes from a completed, validated executor result.** The executor computes SHA-256 over the complete raw response (`landing_live_executors.py:473–535`). `landing_http.py:310–321` validates the result before draft decoding and excludes `result` from the pre-validation failure path. The sole call supplying `result` to `_terminal` is the subsequent decoder failure path (`:323–330`); `_terminal` uses its existing digest (`:355–362`). Invalid type, stdout, digest, elapsed time or usage values still take the generic synthetic-evidence path. The new exact-envelope and invalid-metadata regression cases inspect this boundary independently (`test_landing_failover_providers.py:114–199`).

3. **Usage, disposition and refusal semantics remain compatible.** Decoder refusal stays `needs_human`, with no spec/artifact, category `draft`, and `dispatched=true`. The observation retains the validated reported usage while terminal evidence retains its historical zero counters and `provider_unavailable` disposition (`landing_http.py:327–370`). Existing evidence validation still accepts that disposition (`landing_provider.py:281–288`). Failover tests include the draft refusal (`test_landing_failover.py:126–132`), and the actual coordinator only advances for `FALLBACK_CATEGORIES`, which excludes `draft` (`landing_observation.py:14`; `landing_failover.py:118–124`). Its usage view consumes the reported observation counts (`landing_failover.py:166–177`).

4. **Persistence remains atomic and scoped to the original job.** The service copies reason, evidence digest and observation from the same rejected outcome (`landing_service.py:416–423`). The unchanged store updates all three in one transaction with tenant/repository/job and revision predicates (`landing_sqlite_store.py:232–269`). Decode checks the source identity and independently validates sealed observation/evidence contents (`:640–704`). No new tenant, key, lookup or index path is introduced.

5. **Restart and authenticated reads preserve terminal records.** Store startup recovery selects only accepted/in-progress states (`landing_sqlite_store.py:386–420`), so the new and historical `needs_human` rows are excluded. The authenticated v2 endpoint calls the existing read-only service projection (`landing_backend_api.py:42–50`; `landing_service.py:341–358`). The new regression submits through API/service/SQLite, reconstructs the store and app, rejects an invalid bearer, compares complete sealed receipts and revisions, and installs an executor that fails on replay (`test_landing_failover_backend.py:136–218`). Legacy v1 job/result shapes remain explicitly closed (`landing_service.py:81–100`) and are checked after restart.

6. **Sealed historical formats remain intact.** Observation schema version 1 still has an exact key set and validates its full digest (`landing_observation.py:46–66`). The `/v2/.../attempt` endpoint still carries the existing schema-version-1 attempt receipt, with unchanged nested evidence decoding and seal/binding checks (`landing_failover_contracts.py:39–80`; `landing_contracts.py:475–507`). The frozen generic receipt includes its original synthetic response hash and all seals; the new historical test compares the entire receipt plus the stored reason, evidence digest, noncanonical observation bytes and revision before/after read (`test_landing_failover_backend.py:220–253`). The existing v1-database migration characterization still retains `observation=None` (`:94–111`); the unchanged store decoder preserves SQL NULL (`landing_sqlite_store.py:666–667`). No diagnostic is fabricated for an old record.

7. **Rollback requires no data rewrite.** All store, service, observation, evidence, receipt, backend API and failover consumer files listed below are byte-identical to the base. Their existing validators admit the bounded new reasons and the retained 64-character digest. Restoring the prior compatible application revision can therefore read these rows through the same parsers without a reverse migration or backfill. Query plans, indexes, locks, recovery batch limits and SQL schema version 2 are unchanged; there is no new volume-dependent operation or downtime requirement. The change package's rollback statement matches the code.

## Verification examined and limits

- Read the supplied affected-suite output: 92 tests passed in 4.599 seconds. Reviewed the added tests themselves, not only the summary.
- Read `.grok-stack/runtime/issue152-verification.json` and the composed report. The original full invocation has status `fail` solely for the local Git target metadata check; all test and source-stability checks passed. The original report SHA-256 is `bf5e31b8ee6f5dc65c017c37d14903acf4e682da72f8b17f02bf835342b65f86`, matching the durable provenance. The composed report passes the repaired Git check on the same fingerprint `2c3d1ec45d2ec2b56b5622a98ca524bb0040030231be2eb1e429702fb4633b96`.
- Examined `evidence/verification.json`: 785 core tests plus 1,098 subtests, 774 factory tests including disposable PostgreSQL/restart checks, and the other listed profiles passed. Independently recalculated all five changed product/test file hashes; each matches the verification record. Independently compared the surrounding consumer files with the base using `git show`; each is unchanged.
- This reviewer ran static inspections and hash/base comparisons only. No additional test run was needed for a concrete unresolved risk, so no full suite was repeated. Runtime/provider behavior and an actual installed-code rollback were not exercised by this review.
- Review/report paperwork makes broad receipts stale; this report does not claim the final repository fingerprint is still the test-run fingerprint. The controller owns final fingerprint binding and review receipts after reports freeze. Local evidence is not external Trust CI or merge authority.
- No credentials or production databases were read, no provider/runtime calls were made, and no source, schema, production state, commits or remote branches were changed. The only reviewer write is this report.

## Inspected file identities

SHA-256 values captured from the reviewed tree. The first five match `evidence/verification.json`; the remaining files are unchanged from the stated base.

| File | SHA-256 |
| --- | --- |
| `factory/src/adaptive_factory/landing_http.py` | `21c03d67fe6f2db1126238397d59e4fec5d38c17de6a82de2eb22d565ca01ddc` |
| `factory/tests/fixtures/landing-legacy-draft-attempt.json` | `55b684d1a6603b2a4da3e9ef7ecda75656e96d004e9e0f4e1d36837ef3a11d1c` |
| `factory/tests/test_landing_failover_backend.py` | `77628b032986c6643aa27bb00392204f1de6244a16f0f972a1714fe8bc308ad7` |
| `factory/tests/test_landing_failover_providers.py` | `c5ced5327e4608c8656bbdb3f2e96faa4523820c2762589aa80bb7da015d3841` |
| `factory/tests/test_landing_live_executors.py` | `107a4da22510b43f658524d88484bf46d6f3626b232a383a0ff165bc700996f8` |
| `factory/src/adaptive_factory/landing_provider.py` | `b8ac2f69d970fa1dc50f7b48dd4e0553295104b52248a26f5ad5633a02ef75cd` |
| `factory/src/adaptive_factory/landing_normalizer.py` | `f6cc54452df605e9bcfbf163d0ce567cb1c74ece4501f29a9292674af30fbf9e` |
| `factory/src/adaptive_factory/landing_contracts.py` | `e69b8f754570a62bc168e0c73069b398e6166699127386c8ba69e4c8753cc6d8` |
| `factory/src/adaptive_factory/landing_live_executors.py` | `7740029790856681ce87053c7aabc2db4b0f915f39889be20ed3b18a65de99a6` |
| `factory/src/adaptive_factory/landing_observation.py` | `01a67fc19a28965bfb003f0cb89549c49429220eec8fe7edd9eee3eae2bdeeb2` |
| `factory/src/adaptive_factory/landing_service.py` | `a19cebbde01bf9ce013ad6ed9a77e62e81e9e26006874739d60a1bcf8ac0a598` |
| `factory/src/adaptive_factory/landing_sqlite_store.py` | `378e3eb9ee47e086c21da28768a447fdd65392acfcdd509ed61fc8b44e666caa` |
| `factory/src/adaptive_factory/landing_failover_contracts.py` | `6f6a344a1f3c58220b5b215f668c4b084c81fb08afa873f1606c323692bc0ad1` |
| `factory/src/adaptive_factory/landing_backend_api.py` | `b9f7b6b69553d67f98cf4eff7a5bbe442f99e37c66dad88bae3800b36db51589` |
| `factory/src/adaptive_factory/landing_failover.py` | `308402cb0795a70ad7dfb71944fa68cafd7dc9b029371f175228f084b9bf6a01` |
| `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json` | `85e6f6aec9199d6d69bbc3ee00557fddca8b0f5c5d2a020ffe7e5a11b07e4b1b` |
| `factory/contracts/jsonschema/landing-provider-observation.v1.schema.json` | `94788fc20159c612654d8122713e1218ffc65ab1e11a6238fa45ded2ae8d0a59` |
| `factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json` | `888ddf6ee0042cb332ae17904d1c0f7269894e863ee37ba3b7a950e463bc9eeb` |

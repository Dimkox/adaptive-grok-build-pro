# Minimal data path

HttpLandingNormalizer validates executor metadata, decodes the draft, and on a controlled failure produces an allowlisted reason plus evidence retaining result.response_digest. Existing LandingApplicationService transition atomically persists reason_code and observation_json. The sealed v2 attempt receipt already carries both; the closed v1 projection is unchanged.

There is no migration/backfill or new data field. No index, query-plan, lock or downtime impact is introduced by this patch. Legacy evidence parses exactly as before; old synthetic failure digests and generic reasons are not replaced. Unknown failure details never cross the provider-output boundary. Keep the current decoder exception catch scope; unrelated malformed-type handling is not bundled here.

# Recovery

Record format and database schema are unchanged. Previous code can parse the existing bounded reason field and independently validate retained evidence digests. For source rollback, restore the previously deployed code/config together and keep current records; no reverse migration or backfill is needed. Runtime rollout/backup/acceptance uses a separate exact operational route after this source is merged.

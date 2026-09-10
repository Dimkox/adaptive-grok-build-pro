# Rollback and recovery

This documentation proposal can be revised by a later documentation commit.

The proposed source delivery defaults to unavailable. Use only an additive versioned migration; preserve migrations 001–018 and prior consumers. No invented historical-acceptance backfill is allowed. On defect, disable the new ingestion/reader binding, preserve evidence and repair forward. No destructive down migration or production SQL is included.

# Data architecture analysis — issue #128

Route 3822310b0593; read-only.

- The official PostgreSQL image supplies an anonymous PGDATA volume; `docker rm -f` does not remove it. Prefer a unique named volume with the same 32-hex nonce label as its container, explicitly mounted at `/var/lib/postgresql/data`.
- Before removal, inspect exact container ID/name/image/state/nonce and mount; inspect exact volume name/driver/nonce. Fail closed on any mismatch. Recheck immediately before delete.
- Track the volume as soon as create succeeds so failed container creation cleans it. Recovery must also handle volume-only leftovers and ensure no container references them.
- Existing phase limits sum to roughly 19 minutes, but the gate's outer cap is 600s. Bound aggregate execution below that limit with cleanup margin, then set TTL above the bounded maximum (e.g. 30m).
- Tests: stale running/exited owned resources removed; fresh, malformed, foreign, mismatched, and concurrent resources retained; partial creation cleanup; TTL boundary and exact volume/container binding.

# Architect analysis — issue #128

Route 3822310b0593; read-only.

- Use a unique nonce-labelled explicit volume mounted at PostgreSQL PGDATA and tie it to the exact container by inspected mount metadata.
- Startup reaper is local to the harness, bounded, and limited to old exact-label resources past a conservative TTL; current nonce and ambiguous bindings are preserved.
- Cancellation is a process ownership problem: stop/reap descendants before Docker cleanup. SIGKILL/host loss is recovered on a later TTL sweep, not claimed as immediate cleanup.
- Inner/outer budget expiry must report phase, elapsed, and budget while remaining a failed gate. Leave headroom for cleanup under the existing 600s outer bound.
- Tests must cover concurrent/fresh preservation, ambiguous identities, cancellation order, partial volume creation, and timeout-vs-assertion distinction.

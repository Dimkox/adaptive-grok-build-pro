# Architecture analysis (read-only)

Use an additive local workflow layer with frozen typed intent, ledger, lens, finding, convergence, snapshot, provenance, observation, and journal contracts. A pure resolver produces a complete repair plan or blocks before mutation. Finite lenses cover lineage, dependency consistency, readiness, evidence freshness, pin equality, and one-writer authority; convergence terminates as `ready`, `blocked`, `needs_human`, or `iteration_limit`.

Canonical content-addressed snapshots bind intent/ledger/snapshot digests, controller version, exact HEAD/tree, and prior journal digest. The journal is append-only, CAS guarded, bounded/resumable, atomically written with fsync/rename, and fails closed on corruption. There is no new database, queue, service authority, GitHub Action, webhook, write API, auto-update, PR/push/merge/release/deploy, approval, credential, or Trust-CI coupling. No edits were made.

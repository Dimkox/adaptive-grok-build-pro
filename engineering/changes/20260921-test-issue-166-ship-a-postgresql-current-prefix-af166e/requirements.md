# Requirements

- Real recorded migration prefix upgrades with exactly the current final packaged resource and matching on-disk digest; the full ledger and replay are verified.
- The populated fixture and pre-existing function OID, owner, ACL and effective privileges survive replacement.
- Real synchronized contention completes after release, and sustained migrator advisory contention cancels within a watchdog, leaves the prefix intact, and permits successful retry.

Packaged SQL resources 001–021 and production migrator, timeout values, authority freshness and privilege definitions remain byte-identical.

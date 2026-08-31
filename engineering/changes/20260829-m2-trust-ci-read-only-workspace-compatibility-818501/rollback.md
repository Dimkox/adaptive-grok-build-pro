# Rollback plan — M2 Trust CI read-only workspace compatibility

## Trigger conditions

- Exact-path Git trust is broadened, persistent, or unable to support the pinned different-owner checkout.
- Packaging mutates source bytes or changes archive/sidecar compatibility.
- Packaging follows a symlink/non-regular source, accepts identity/content drift, publishes a partial archive, or performs an unbounded source/archive read.
- Temporary archive writes can be redirected by pathname substitution, output permissions drift, or descriptor-validation failures leak/raw-error.
- Receipt clone drops `--no-local` or reads host Git configuration.

## Application rollback

Apply one forward-fix that reverts the architecture invocation, pure renderer/package construction, and receipt-fixture config patch together. Do not weaken the read-only mount, ownership boundary, mutation detector, or deployed Trust CI policy to restore compatibility.

## Data recovery / forward-fix

No migrations, databases, external systems, or durable runtime state are changed. Archive outputs are disposable build artifacts; remove and regenerate them after the forward-fix if necessary.

## Verification after rollback

Re-run the Git, source-manifest, external-symlink, replacement-race, streaming-checksum, and receipt regressions plus `tests.test_manifest_package`; confirm the repository source remains byte-identical and the pinned runner preserves `/workspace:ro`, `.git:ro`, and non-root execution. A rollback that restores any confidentiality, integrity, memory, or original compatibility RED is not releasable.

# Requirements — M2 Trust CI read-only workspace compatibility

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] **AC-001:** Given a different-owned repository and an isolated Git environment, every architecture Git operation applies `safe.directory` only to the exact canonical root in that command's argv and succeeds without persistent configuration or writable Git metadata.
- [x] **AC-002:** Given a pre-existing source `MANIFEST.sha256`, packaging preserves those bytes exactly and embeds a freshly rendered deterministic manifest in the ZIP while retaining archive modes, exclusions, ordering, and checksum sidecar behavior.
- [x] **AC-003:** Given the exact receipt regression, its `git clone --no-local` uses a temporary process-scoped global config that trusts exactly `ROOT/.git`, disables system config, and does not mutate user or repository configuration.
- [x] **AC-004:** Given the final 10,739-line measured compatibility change, architecture fitness passes under an explicit finite `max_changed_lines: 10820` repository rule.
- [x] **AC-005:** Given hostile source/output/checksum entries or output-path ancestors, packaging binds operations to held descriptors, rejects untrusted rename authority, creates missing parents privately, and atomically replaces from exclusive regular inodes without opening existing sidecar names.

## Failure and edge cases

- Missing or invalid Git revisions continue to fail closed with the existing typed architecture error.
- Repository Git commands use the resolved canonical root; non-repository `git diff --no-index` remains isolated without acquiring repository trust.
- A source manifest may be absent or contain stale/arbitrary bytes; neither case changes the archive's newly rendered manifest.
- Symlinks and all non-regular source entries are excluded; a symlink or replacement introduced after enumeration fails closed at the no-follow descriptor boundary.
- Each archive member must retain the same device, inode, mode, size, timestamps, and content digest observed during manifest hashing.
- A successful publication must resolve to the held regular archive inode; mismatch removes the non-authoritative output entry, fails before sidecar publication, and never opens its replacement for content or checksum reads.
- Output-parent creation precedes one canonical no-follow directory open; existing-output inspection, mode capture, temporary creation, replace, validation, cleanup, and sidecar publication then use only that held parent fd.
- A parent not owned by the effective UID, a group/world-writable parent, or a relocated/rebound requested parent fails with controlled `PackageError`.
- Every requested and canonical ancestor owner is effective UID or root; group/world-writable non-sticky ancestors and unsafe intermediate aliases are rejected, while root/effective-UID-owned sticky ancestors are accepted only when the child is effective-UID-owned.
- Missing final/intermediate output parents are created no-follow relative to the bound ancestor, bound and set to exact `0700` independent of ambient umask, and revalidated without chmod-mutating pre-existing directories.
- New archives use kernel `0666 & ~umask`; replacement of an existing regular non-symlink archive preserves its permission bits.
- A symlinked repository root remains a supported alias for the canonical regular-file enumeration.
- Every failed post-open descriptor validation closes the descriptor and raises `ManifestError`.
- Descriptor-relative packaging fails with a controlled error when its POSIX capabilities are absent; explicit manifest generation and verification remain compatible without importing those flags eagerly.
- Same-UID or privileged actors and concurrent mutation inside the required private parent are trusted and out of scope; no portable zero-transient claim is made, and consumers may act only after successful return with the held-inode output and sidecar present.
- Existing sidecar names are inspected without following or opening; symlink, hardlink, FIFO, and other replaceable entries are atomically replaced from an exclusive held regular fd, directories are rejected before archive publication, and existing regular mode bits are preserved.
- The receipt test removes its temporary Git config with its existing temporary directory and never relies on host global/system Git configuration.

## Non-functional requirements

- Security: never use `safe.directory=*`, global config writes, arbitrary inherited Git configuration, ownership changes, writable `.git`, or deployed trust-plane changes.
- Reliability: source bytes are invariant across successful packaging and the required `--no-local` clone remains in place.
- Performance: use bounded chunks for source hashing, ZIP streaming, and final archive checksum; never allocate an entire source file or completed ZIP.
- Observability: focused regressions identify architecture trust, archive source invariance, and receipt-clone compatibility separately.
- Governance: architecture, governance, and security approval scopes are required for the rule and packaging-boundary adjustment.

## Contract compatibility

OpenAPI, JSON Schema, and event contracts are explicitly unchanged. This repair changes only local Git invocation policy, package construction internals, and test-fixture isolation.

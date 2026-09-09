# Architecture — M2 Trust CI read-only workspace compatibility

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Architecture helpers replace the outer runner Git environment with an isolated configuration but do not re-add exact repository trust, so different-owner repositories fail as dubious. The packager calls the source-writing manifest generator and later unlinks the source manifest; the receipt fixture invokes `git clone --no-local` without a config visible to the child `upload-pack` process.

## Proposed behavior

Resolve the repository root once per architecture Git operation and add `-c safe.directory=<canonical-root>` to that command only. Split explicit manifest generation from a secure snapshot: enumerate regular files only, open the root and every descendant component descriptor-relative with `O_NOFOLLOW`, bind identity plus digest, and require the same identity/digest while streaming to an atomically published ZIP. Give only the receipt test clone a temporary config containing the exact source `.git` path.

## Components and boundaries

- `.grok-stack/adaptive_grok/architecture_diff.py`: owns isolated Git execution and exact command-scoped repository trust.
- `.grok-stack/adaptive_grok/manifest.py`: owns regular-file enumeration, descriptor-relative no-follow snapshots, identity/digest stability, bounded streams, and pure manifest rendering; explicit generation remains the only source-writing manifest operation.
- `scripts/package_stack.py`: owns secure ancestor/private-parent validation and creation, one held parent fd, separate exclusive archive/checksum fds, verified replacement, cleanup, and sidecar publication, not source-tree metadata.
- `tests/test_change_receipts.py`: owns its temporary clone configuration and cleanup.
- `architecture/rules.yaml`: owns the explicit finite 10,820 changed-line fitness ceiling.
- `trust-ci/**`: outside this change and unchanged.

## Data flow

1. Architecture caller supplies a repository root and revisions.
2. The helper resolves the root, builds an isolated environment, and invokes Git with exact command-scoped trust.
3. Packaging enumerates regular source paths once, snapshots each through no-follow root-relative descriptors, and records stable identity plus digest.
4. It reopens the same descriptor-relative identity, streams and re-hashes one file at a time into a temporary ZIP, and aborts on metadata or digest drift.
5. It verifies trusted/non-renamable ancestors, privately creates missing parents, binds the effective-UID-owned parent once, and publishes the ZIP and checksum from separate exclusive held regular fds using only parent-relative operations.
6. The receipt fixture writes one temporary Git config, passes it only to `clone --no-local`, and removes it with the temporary directory.

## API and event contracts

No OpenAPI, JSON Schema, event, queue, webhook, producer, or consumer contract changes. `generate_manifest(root)` remains backward-compatible and explicit; `render_manifest(root)` is a new pure internal helper.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: archive content remains compatible; source mutation is removed.
- Core modification: none; Bitrix is not in the routed domain.

## Decisions

- Put exact trust in each repository Git command rather than in persistent or inherited config.
- Render archive metadata in memory and keep source-writing generation explicit.
- Preserve `--no-local`; isolate only the test fixture config needed by the clone's child process.
- Bind source authority to root-relative no-follow descriptors and require stable identity plus digest across hash and ZIP phases.
- Keep archive/checksum authority in separate exclusive no-follow fds and output-name authority in one private parent fd through construction, atomic publication, identity verification, and cleanup.
- Admit the measured 10,739-line change with a narrowly raised 10,820-line repository architecture ceiling rather than reducing security or streaming behavior.

## Risks and mitigations

- **Overbroad Git trust:** exact resolved path assertion plus wildcard rejection in the real-repository regression.
- **Archive drift:** existing deterministic archive, mode, exclusion, sidecar, and installer tests remain in the focused package suite.
- **Hidden source mutation:** regression begins with sentinel manifest bytes and asserts byte-identical preservation after packaging.
- **External-path disclosure or TOCTOU:** symlinks/non-regular files are excluded, every parent/file open is no-follow and root-relative, and identity plus digest mismatch aborts before atomic publication.
- **Memory exhaustion:** all source, ZIP member, and completed-archive hashing uses fixed-size streaming chunks.
- **Temporary/output pathname substitution:** random `O_EXCL|O_NOFOLLOW` sibling creation retains the archive fd and digest authority, while all names resolve relative to one held private-parent fd; a detected mismatch is removed and cannot return success or create a new sidecar.
- **Sidecar redirection/liveness:** an existing sidecar is never opened; a held exclusive regular temp is written and verified before atomic replacement, so hardlinks are not mutated and FIFOs cannot block.
- **Ancestor relocation:** requested and canonical ancestor owners, aliases, and rename permissions are checked; non-sticky shared writers are rejected, normal trusted sticky `/tmp` is supported, and missing parents are created at `0700`.
- **Portable publication boundary:** same-UID/privileged actors and concurrent mutation inside an enforced authority boundary are trusted and out of scope; consumers use the archive only after successful return and sidecar publication, so the design makes no literal zero-transient guarantee.
- **Platform capability drift:** descriptor flags are discovered only by secure packaging; missing POSIX capabilities produce a controlled failure while explicit manifest generation and verification remain usable.
- **Permission compatibility:** kernel umask determines a new archive mode; existing regular archive permission bits are applied to the replacement fd.
- **Trust-boundary expansion:** no `trust-ci/**`, runtime, policy, signatures, approvals, or external state changes are in scope.
- **Architecture budget growth:** the rule remains finite, leaves 81 measured lines of headroom, and requires architecture, governance, and security approval.

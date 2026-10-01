# Factory Linux setup manager

`setup_manager.py` is a Python 3.11+ stdlib release lifecycle policy. Its default
imports no application/web/database stack and executes no subprocesses. `install_into.py`,
inactive L5 preparation, Factory storage, and Trust CI authority remain unchanged.

## Release contract

Supply a ZIP, separate UTF-8 JSON manifest, and independently trusted SHA-256
digests for **both**. Sidecar digests alone do not authenticate a publisher.
Existing source ZIPs are not implicitly runtime releases in this format.

```json
{
  "schema_version": "factory-release/v1",
  "product_version": "1.0.0",
  "profile": "factory-python",
  "data_schema": 1,
  "files": [{"path": "app/main.py", "size": 15, "sha256": "<64 lowercase hex digits>", "mode": 420}]
}
```

`size`/`sha256` bind exact uncompressed bytes. `mode` is decimal 420 (`0644`) or
493 (`0755`). ZIP entries are exactly those regular files with Unix mode metadata.
Links, directory/special entries, traversal, aliases, duplicate/extra/missing files,
and file/directory collisions fail closed. Paths use ASCII letters/digits, `_`,
`-`, `.`, `/`; root `.factory-release.json` is reserved. Duplicate/unknown JSON
keys fail. Versions are semver-shaped; data schema is a nonnegative identity.

Limits: archive 128 MiB, payload 64 MiB, file 16 MiB, 4096 files, JSON 1 MiB,
paths 512 characters/32 segments. Captured verified bytes are staged without
`extractall` and rechecked before runtime use. Identity is SHA-256 of concatenated
archive/manifest hex digests. Directories become `0555`, files `0444`/`0555`.
Digest release directories are never overwritten.

## CLI and explicit runtime adapter

```sh
python3 factory/runtime/setup_manager.py preflight --root /absolute/private/factory
python3 factory/runtime/setup_manager.py verify --root /absolute/private/factory \
  --archive release.zip --manifest release.json \
  --archive-sha256 ARCHIVE_SHA256 --manifest-sha256 MANIFEST_SHA256
python3 factory/runtime/setup_manager.py status --root /absolute/private/factory
```

CLI returns `factory-preflight/v1`, `factory-status/v1`, or `factory-error/v1`
JSON; failures expose closed codes and exit 1. `verify` returns the digest.
Malformed CLI syntax is argparse exit 2. The standalone CLI defaults to **no runtime
adapter**. Lifecycle effects fail with `ADAPTER_REQUIRED` when needed. An authorized
operator wrapper can inject one through `main(argv, adapter=...)` or `SetupManager`.
CLI update/reversal have no backup provider and fail closed. No Docker, systemd,
credentials, or production-host integration is implied.

### Explicit Ubuntu process profile

`linux_process_adapter.py` is opt-in for exactly Ubuntu 24.04 x86_64 and
`/usr/bin/python3.12`. Use `setup_manager_linux.py ... --runtime-config
/absolute/private.json`; the ordinary setup-manager CLI remains adapter-free.
The owner-only (`0600`) JSON has this closed shape; the separately existing runtime
directory must be owner-only `0700` and short enough for AF_UNIX:

```json
{"schema_version":"factory-linux-process/v1","python":"/usr/bin/python3.12","runtime_directory":"/run/user/1000/adaptive-factory","environment":{}}
```

Only bounded `FACTORY_*` environment entries are accepted; `FACTORY_SOCKET_PATH`
is adapter-owned. The child receives a clean fixed environment and exact argv
`/usr/bin/python3.12 -m adaptive_factory.server`, with `PYTHONPATH` bound to the
selected immutable release. It uses no shell, root, systemd, package manager,
network, or migrations. Each release gets a distinct UDS, private log and durable
PID record bound to release, boot ID, PID/PGID, `/proc` start time, cmdline and argv
digest. Stop pins the live leader and every observed group member with pidfds before
TERM and a bounded KILL fallback, and cannot target its own group. This cleans
resistant descendants during owned startup/stop without a validate-then-PID-reuse
signal race. A stale boot or leaderless persisted group blocks restart and signalling
for explicit recovery; it is never mistaken for an absent release. Readiness uses a
stdlib UDS `GET /health/ready`.
Windows is unsupported and macOS is excluded.

Config and runtime paths are opened component-by-component through owner-pinned
`O_NOFOLLOW` descriptors; the child inherits only the pinned runtime-directory
descriptor used for its UDS. Intermediate symlinks and mutable unsafe ancestors are
rejected. Application stdout/stderr is deliberately discarded: the adapter's private
on-disk log contains bounded lifecycle signals only and is tail-truncated at 64 KiB.

### Deterministic offline builder

`build_offline_release.py` accepts an exact clean Git HEAD, a wheelhouse containing
exactly `runtime-wheels-linux-x86_64-cpython312.json`, and an output stem. The
inventory is checked against `uv.lock`; every wheel filename/SHA-256 must match,
with no extras, dependency resolver or network access. The builder safely expands
wheels and tracked `factory/src/adaptive_factory` bytes, rejects unsafe entries and
collisions, emits canonical sorted ZIP metadata plus detached manifest/digests,
then self-verifies through the setup manager before publishing outputs.

```sh
python3 factory/runtime/build_offline_release.py \
  --repository "$PWD" --expected-head "$(git rev-parse HEAD)" \
  --wheelhouse /absolute/offline-wheelhouse \
  --inventory factory/runtime/runtime-wheels-linux-x86_64-cpython312.json \
  --output /absolute/output/factory-0.1.0 --product-version 0.1.0
```

`RuntimeAdapter` requires read-only preflight/status/health/logs and exact-release
start/stop. Each call receives a 30-second timeout; logs receive byte/line limits.
The trusted adapter must enforce bounds, authorize effects, isolate candidate and
prior runtimes, and keep start/stop free of migrations. The manager checks elapsed
time after return but cannot cancel arbitrary injected Python callbacks. Adapters
must pre-redact arbitrary secrets; the manager additionally redacts credential
lines, PEM blocks, and nonprinting control sequences.

## State, recovery, and removal

The dedicated root is UID-owned `0700` with safe ancestry; its parent must exist.
Read-only Linux preflight checks available memory/disk and optional loopback port
conflicts (checks do not reserve ports). Occupied roots need matching install state.
An interrupted first initialization may contain only an exact UID-owned `0700`
subset of the six empty managed directories and an empty private state lock. This
pristine topology can be retried or reconciled; unknown entries, data bytes, links,
unsafe modes, and temporary journal files require explicit investigation. Recovery
checks the topology again under lock before writing the initial journal.
Root privacy is the trust boundary; hostile same-UID/root processes are outside it.
Use a local filesystem supporting flock, atomic rename, and fsync.

`state/install.json` (`factory-install/v1`) records root, generation, phase,
current/previous digests, retained schema, operation ID/candidate/prior. The lock
uses nonblocking flock; journal/pointer transitions use atomic writes and fsync.
The optional additive `last_transition` field retains one bounded last successful
version transition: original operation ID/kind/prior/candidate, backup relative
path/digest, prior/candidate schemas and compatibility decision, runtime-preflight
and health observations, and completion generation. Restart/stop/removal preserve
this record. It is observed workflow evidence, not signed human approval or proof
that a retained backup still exists; each new transition rechecks actual backup bytes.
`current` is a relative `releases/<digest>` symlink switched only after health.
Status separates persisted phase from observed `running` (`null` without adapter).

`update(**artifact, evidence=TransitionEvidence(...))` and `reverse(digest, evidence=...)`
require a retained regular backup under this root's `backups/`, checked SHA-256,
and exact root/prior/candidate/schema binding. Only the **same schema** is supported;
there is no migration/down-migration callback. Backup bytes prove retention and
integrity; operators must establish actual snapshot completeness and restore drills.

Interrupted operations block mutation until `reconcile()`. A prior pointer stops
the candidate; a candidate pointer needs fresh health and stops the prior. Recovery
replays no start/migration and retains partial staging. Ordinary interrupted removal
can reconcile while preserving data; interrupted purge requires separate operator
recovery (`RECOVERY_REQUIRED`) and never silently resumes deletion.

`remove()` stops current runtime/clears its pointer but preserves releases, data,
config, backups, logs, and state. Reinitializing retained data with install is blocked.
Read-only `purge_token()` binds the absolute root/inode, generation/current, and
metadata inventory of exact releases/config/data/backups/logs targets. It confirms
targets, not authority. `remove(purge=True, token=...)` validates under lock before
effects, deletes those five trees, and retains audit state. Changes invalidate the
token; deletion requires independent backups for recovery. Links/hardlinks/special
entries fail closed. The installation root is never recursively deleted.

## Provenance and qualification

Safety patterns were adapted with explicit owner authorization from
`Dimkox/liqvera@e3df6833e8916d01f55028e63d4db1632a805a75`:
`scripts/verify-liqvera-installer.py`, `installer/lib/runtime.py`, and `lifecycle.py`.
The upstream tree has **no root open-source license**. Owner-directed transfer is
recorded in the change package; it makes no upstream open-license claim. This newly
written Factory code contains no Liqvera service/config/image/Compose/Caddy/migration
payload. The opt-in Linux adapter is Factory-specific new code.

The checked-in [`setup_manager.provenance.json`](setup_manager.provenance.json)
pins the upstream SHA/reference hashes and records the owner's 2026-09-30 direction:
“https://github.com/Dimkox/liqvera отсюда прототип инсталлера забери”. Its scope is
inspection/selective prototype safety-pattern reuse, not a license grant, signed
security approval, or host operation. No temporary inspection checkout is needed to
understand this record.

`python3 -m unittest factory.tests.test_runtime_installer
factory.tests.test_linux_process_adapter factory.tests.test_offline_release_builder`
adds real local child/UDS lifecycle and deterministic builder coverage to the private
temporary-root archive/digest/lock/journal suite. It establishes no production-host
acceptance, database availability, backup restore qualification, or deployment authority.

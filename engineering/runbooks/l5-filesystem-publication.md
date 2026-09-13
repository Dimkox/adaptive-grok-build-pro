# L5 owner-controlled filesystem publication

The F/G source implements a concrete owner-controlled filesystem adapter without assuming a cPanel API, SSH command or document root. See [the final G package](../changes/20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b/brief.md) and its exact-source evidence policy. Landing API v1 and its unavailable publisher remain intact; v1 results retain `live_url: null`. Source preparation has no production acceptance or deployment.

The separate entrypoint is `python3 scripts/grok_landing_publish.py`. Its `prepare`, `observe`, `status`, `reconcile` and explicitly enabled `apply` phases compose existing source packages directly; no dependency or service is added. The factory bridge opens landing SQLite read-only, validates the full tenant/repository/job identity, revalidates the retained artifact/evidence/manifest, and takes a bounded ZIP byte snapshot. Delivery then independently validates archive identity, confinement, sizes, modes, hashes and Git source/candidate provenance.

The adapter requires a deliberately provisioned private root owned by the serving operator at mode `0700`. The actual owner UID, device and inode are part of `PublicationTargetV1`; path substitution fails closed. Trusted nonsymlink ancestry is required. The root must contain a pre-provisioned owned, single-link mode-`0600` `.publication.lock` file. Runtime observation does not create it. The web server must be configured separately to serve only `current`, under an identity permitted to traverse this private root; this source does not alter the server's configuration.

The closed mode-`0600` operator config contains these fields:

```json
{
  "schema_version": 1,
  "control_repository": "/absolute/control-checkout",
  "route_id": "the-current-route-id",
  "change_id": "the-current-change-id",
  "publication_state_root": "/absolute/private-publication-state",
  "landing_state_root": "/absolute/private-landing-state",
  "tenant_id": "the-authorized-tenant",
  "repository_id": "github.com/Dimkox/ai-dark-factory-landing",
  "target": {
    "schema_version": 1,
    "target_id": "the-approved-host-target",
    "root": "/absolute/private-release-root",
    "public_origin": "https://therealaidarkfactory.online",
    "owner_uid": 0,
    "device": 0,
    "inode": 0
  }
}
```

All sample paths/identity numbers are placeholders, not discovered target facts. State roots, target and control checkout must be disjoint and pre-existing; double-slash path anchors are rejected at config, target and filesystem-root boundaries. The artifact output root must also be separate. Target origin must equal the artifact's canonical origin; config cannot silently repurpose the artifact to another site.

For a separately approved artifact, `prepare --action stage --request-id <stable-id> --job-id <job-id> --config <path>` persists exact request body, artifact identity, target identity and observed baseline before any publication write. It prints `request_digest` and literal `resource`. `prepare` changes only the private publication intent database and performs read-only artifact/target observations. A repeated request ID cannot be repurposed.

`apply --live --request-digest <digest> --config <path>` independently checks the current control repository origin, active route/change, Git HEAD and adaptive tree fingerprint against exactly one unexpired delegated local grant with scope `external-write`, action `external-write` and resource `landing-publication/v1/<stage|activate|restore>/<request-digest>`. The grant must already materialize explicit user consent through the existing approval mechanism, with an exact singleton action/resource and at most the issuer's 24-hour lifetime. Only explicit GitHub HTTPS, SCP-style SSH and ssh://git@github.com remote forms are accepted; misleading host suffixes are rejected. Direct product CLI apply without the repository entrypoint's authorization callback fails before configuration or state access. This CLI never creates grants, human signatures, security approvals or Trust CI evidence. A local grant supplies no external acceptance or merge authority.

The callable-presence check precedes configuration/state access. Exact grant validation follows the saved request and required artifact/target observations, and precedes the `inflight` transition and filesystem effect. Observation-only recovery can persist local intent observations without a publication grant. Before an effect, the coordinator revalidates the artifact, target baseline and grant, then commits phase `inflight` together with the authorization digest. Stage creates `releases/<artifact-digest>/site` using exclusive file/directory creation, confined archive members and fsync. Completed files are mode `0400`, directories mode `0500`; `release.json` beside the site retains the exact artifact and manifest. Partial directories remain preserved and are never overwritten/resumed automatically.

Prepare `activate` for the same job after a stage result. It requires its own exact grant. Under the target's exclusive cooperating lock, the adapter revalidates current baseline and staged release content, creates an exact relative symlink and atomically replaces `current`. Release directories are never removed or overwritten. SQLite retains the exact predecessor release and manifest.

To restore a predecessor, prepare `restore --restore-from <activation-request-digest>` with a new request ID. The referenced activation must have completed, target identity must match and current state must still be that activation's desired state. Restore requires a separate grant and changes only the pointer back to the recorded predecessor, or removes the pointer when restoring the initially absent deployment. No arbitrary filesystem target is accepted.

Any exception/crash after `inflight` is ambiguous. `reconcile --request-digest <digest>` observes and records success only if the exact desired state exists; otherwise it records `needs_human`, without repeating writes. Later `apply` on an in-flight request also performs observation only. Missing/partial/corrupt state is preserved for operator disposition. Neither recovery nor rollback deletes potentially useful evidence.

`status --request-digest <digest>` opens the intent database read-only/query-only. `observe` reads the target under a shared cooperating lock. Results identify scope `owner-controlled-filesystem`; HTTP origin availability, hosting acceptance, indexing, external Trust CI and signed production approvals are not asserted. Real operational acceptance must be obtained separately before a production claim.

Current regressions use private temporary artifacts/state and synthetic grants: exact/expired/foreign/duplicate authority, identity and remote-host checks, aliases, tamper, link replacement, read-only SQLite, mixed evidence, pointer ambiguity and persisted predecessor restoration. Publication SQLite validates complete supported STRICT table/column/primary-key/unique/index shape and rejects unexpected objects; tests cover unsupported schemas before read/write acceptance. Restart tests exercise committed effects without replay and retained restoration lineage. These are bounded process/fixture observations, not crash-at-every-fsync proof, arbitrary operator race guarantees or real production restoration. G additionally snapshots populated intent state and reopens it through the strict reader. Exact full/review results and external acceptance remain separately required.

The supported publication schema also binds the full application-created CREATE TABLE declaration with case/whitespace normalization only. Changed conflict policies, comments, quoting and extra clauses are outside that closed declaration and fail schema validation; explicit INSERT OR ABORT preserves the original intent on a collision. Existing generated v1 databases and their SQLite backups keep the same schema identity.

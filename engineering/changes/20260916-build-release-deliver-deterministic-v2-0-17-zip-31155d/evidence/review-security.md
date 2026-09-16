PASS

Security review — artifact child of the v2.0.17 release
Route `31155d4d2a6a`, receipt kind `security_review`.
Subject: commit `5b178d3411306143735f6985a1817646e194ea2a` in worktree
`/home/pall/grok-projects/adaptive-grok-build-pro-artifact-217`
(branch `feature/v2.0.17-artifact-child`), base `78082a290f8b90cade88685351fbb2ba263689b9`
(= upstream `main`, the merged v2.0.17 release-sync "R" commit).
Primary contracts: `change-spec.yaml` FORBID-001 (no early publication) and FORBID-002
(no build from a dirty/non-exact checkout, no non-reproducible byte pair).
Reviewer contract obeyed: no `.env`, no private key, no credential store and no
`/etc/adaptive-l5/*` file was opened at any point; service state was read only through
unprivileged `systemctl show`.

---

## 1. Reproducibility integrity — FORBID-002: SATISFIED

### 1.1 Tracked bytes match the recorded digests

Worktree was clean and at the reviewed commit before any measurement:

```
$ git rev-parse HEAD
5b178d3411306143735f6985a1817646e194ea2a
$ git status --porcelain
(empty)
$ sha256sum packages/adaptive-grok-build-pro-v2.0.17.zip packages/adaptive-grok-build-pro-v2.0.17.zip.sha256
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616  packages/adaptive-grok-build-pro-v2.0.17.zip
54db9f64bb7296ca657410131499ca06358f89b23171e221b04e300acf03f3c0  packages/adaptive-grok-build-pro-v2.0.17.zip.sha256
$ stat -c '%s %n' packages/adaptive-grok-build-pro-v2.0.17.zip
10940676 packages/adaptive-grok-build-pro-v2.0.17.zip
```

The Git blob content digests are identical to the working-file digests, so the recorded
bytes are the committed bytes and not merely the on-disk ones:

```
$ git cat-file blob HEAD:packages/adaptive-grok-build-pro-v2.0.17.zip | sha256sum
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616  -
$ git cat-file blob HEAD:packages/adaptive-grok-build-pro-v2.0.17.zip.sha256 | sha256sum
54db9f64bb7296ca657410131499ca06358f89b23171e221b04e300acf03f3c0  -
```

Both digests equal `local_candidate.artifact_child.zip_sha256` /
`sidecar_sha256` read directly out of the current `PROJECT_STATE.json`, and equal the
commit-message claim. Size 10,940,676 B matches the record, the notes field and the diff
stat (`Bin 0 -> 10940676 bytes`).

### 1.2 Sidecar exact text: `<zip-sha>  <zip-name>` + single LF, two spaces

```
$ od -c packages/adaptive-grok-build-pro-v2.0.17.zip.sha256
0000000   7   7   0   f   1   d   b   5   ...   0   f   7   4   6   1   6
0000100           a   d   a   p   t   i   v   e   -   g   r   o   k   -
...
0000140   7   .   z   i   p  \n
0000146
$ cat -A packages/adaptive-grok-build-pro-v2.0.17.zip.sha256
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616  adaptive-grok-build-pro-v2.0.17.zip$
```

Offset `0000100` starts with two space bytes immediately before `adaptive-`; the file is
102 bytes (`stat -c '%s'` → 102 = 64 hex + 2 spaces + 35 filename + 1 LF), ending in
exactly one `\n`, no trailing blank line, no CRLF, and it names the bare filename (no path
prefix), which is `sha256sum -c` compatible inside `packages/`.

### 1.3 Independent rebuild from the recorded `source_parent` — digest reproduced

Private staging, restrictive umask, exact-SHA detached clone, clean-checkout requirement,
build executed **from inside the clone**:

```
$ umask 077; S=$(mktemp -d /tmp/sec-audit-217.XXXXXX); chmod 700 "$S"
$ git clone --no-hardlinks --no-checkout /home/pall/grok-projects/...-artifact-217 "$S/src"
Cloning into '/tmp/sec-audit-217.9Mn9ws/src'... done.
$ git -C "$S/src" checkout --detach 78082a290f8b90cade88685351fbb2ba263689b9
HEAD is now at 78082a2 docs(release): v2.0.17 candidate identity sync (R) after the v2.0.16 publication (#98)
$ git -C "$S/src" rev-parse HEAD           -> 78082a290f8b90cade88685351fbb2ba263689b9
$ git -C "$S/src" rev-parse HEAD^{tree}    -> 2283e6a09d3eb2a0aeabce8a872e06746b941176
$ git -C "$S/src" status --porcelain       -> (empty: clean checkout required and obtained)
$ cd "$S/src" && python3 scripts/package_stack.py --output "$S/probe.zip"
/tmp/sec-audit-217.9Mn9ws/probe.zip
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616
$ sha256sum "$S/probe.zip"
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616  /tmp/sec-audit-217.9Mn9ws/probe.zip
10940676 /tmp/sec-audit-217.9Mn9ws/probe.zip
```

Three independent observations line up: the clone tree `2283e6a0…` equals the recorded
`artifact_child.source_parent_tree`; the third-party rebuild equals the tracked ZIP digest
and byte length; therefore the archive is reproducible from the recorded source parent
alone (INV-002, FORBID-002). The clone was made with `--no-hardlinks` into a `0700`
directory, so the build could not have read the artifact worktree's own working files.
Staging directory was removed afterwards (`rm -rf /tmp/sec-audit-217.9Mn9ws`; the
follow-up `ls` reported `No such file or directory`) and the reviewed worktree is still
clean at `5b178d3` — this review changed no repository file except this report.

### 1.4 Coupled regression evidence passes

```
$ python3 -m unittest tests.test_project_state                          -> Ran 14 tests ... OK
$ python3 -m unittest tests.test_manifest_package.PackageTests.\
    test_published_zip_matches_immutable_release_record_and_embedded_manifest -> OK (0.605 s)
```

That manifest test re-derives the digest from the tracked bytes and asserts the sidecar
string `f"{digest}  {name}\n"`, so the AC-001 gate and this reviewer's recomputation agree.

---

## 2. No early publication claim — FORBID-001: SATISFIED

Read directly from the live `PROJECT_STATE.json` in this tree:

```
status = "artifact_bytes_delivered"          artifact_status = "pending_tag_and_release"
published = false            published_at = null
external_effect = false      external_effect_scope = null
operational_activation = false
checked_head = null          merge_commit = null        tree = null     pull_request = null
reviewed_product_head = null reviewed_product_tree = null
artifact_child.commit = null artifact_child.tree = null
artifact_child.source_parent = "78082a290f8b90cade88685351fbb2ba263689b9"
artifact_child.source_parent_tree = "2283e6a09d3eb2a0aeabce8a872e06746b941176"
artifact_child.status = "built_byte_reproducible_twice"
```

The child names only its parent (knowable before it merges) and self-records nothing about
its own merge, exactly as AC-003 requires. `observed_main_sha` (top level, line 6) and
`local_candidate.source_base` are both pinned to `78082a2…` per AC-002.

Reality matches the record — no tag, no Release exists yet, so nothing is claimed early:

```
$ git tag --list 'v2.0.1*'      -> v2.0.1 … v2.0.16   (no v2.0.17)
$ git ls-remote --tags origin 'refs/tags/v2.0.1*'  -> last entry refs/tags/v2.0.16 (8486ddb6…, target 969c4f65…)
$ gh release view v2.0.17 --repo Dimkox/adaptive-grok-build-pro   -> release not found
$ gh api repos/Dimkox/adaptive-grok-build-pro/git/refs/tags/v2.0.17 -> {"status":"404"}
```

Every added human-readable line that mentions release/publish/tag/install/activate was
reviewed; all of them are in the negative or the future. Representative added lines
(grep over added lines of the diff, ZIP excluded):

- README.md:7 — "…no `v2.0.17` tag or GitHub Release exists yet, so `published` stays false…"
- START_HERE.md:9 — "…the tag and GitHub Release do not exist yet, `published` is still false, and publication requires its own exact delegated actions."
- GROK_BUILD_HANDOFF.md:303 — "…while the tag and GitHub Release do not exist yet, `published` stays false…"
- CHANGELOG.md:19 — "The tag and GitHub Release do not exist yet: publication stays a separate step…"
- packages/README.md:30 — "| `adaptive-grok-build-pro-v2.0.17.zip` | 2.0.17 (artifact delivered, tag and GitHub Release pending) |"
- release.md — tag and Release are written as steps 1–3 with "each needs its own exact delegated grant bound to repository, route, change, HEAD, tree fingerprint and TTL".
- runtime dossier `artifact_state` — "No tag, no GitHub Release, no installation and no activation."

No sentence a reader could take as "v2.0.17 was released/tagged/installed/activated" was
found in README.md, START_HERE.md, GROK_BUILD_HANDOFF.md, CHANGELOG.md,
DARK_FACTORY_ROADMAP.md, packages/README.md, the change package or the runbooks.

The converse check is also clean: a grep for still-asserting-absence wording over the
current docs returns nothing (`grep -riE "(zip|sidecar)[^.]{0,60}(do not exist|does not
exist|absent|no tracked bytes)"` over README/START_HERE/HANDOFF/CHANGELOG/ROADMAP/
packages/README/docs/runbooks → no match), so the R-era "no v2.0.17 ZIP or sidecar exists"
sentences were all flipped rather than left contradicting the tree. Identity literals
were not moved (AC-004): archived `VERSION` = `2.0.17` and
`__version__ = "2.0.17"` (see §3), and no identity file appears in
`git diff --name-status 78082a2..HEAD`.

---

## 3. Archive contents: clean

```
member count: 2895
all members carry adaptive-grok-build-pro/ prefix: True      (bad prefix list: [])
absolute / ".." paths: []
non-regular entries (symlink, fifo, device, hardlink): []     dir entries: 0
VERSION inside archive: 2.0.17
.grok-stack/adaptive_grok/__init__.py: __version__ = "2.0.17"
nested .zip members: none (only MANIFEST.sha256)
```

Name scan for secret-shaped members returned only benign hits, each opened and judged:
`docs/superpowers/{plans,specs}/2026-09-11-token-cache-cost-accounting*.md` (cost-accounting
docs), `engineering/changes/20260915-…-feeb4f/evidence/grok-usage-secret-scan-final.log`
(a scan log, not a secret), and `factory/.env.example` + `trust-ci/.env.example` +
`trust-ci/env/*.env.example` templates. No `.env`, no `*.pem`, no `*.key`, no credential
store is packaged. Content scan of every member ≤3 MB for
`-----BEGIN … PRIVATE KEY-----`, `AKIA…`, `ghp_…`, `xox[baprs]-` found one hit, a
pre-existing August evidence document quoting those very patterns as scanner examples
(`…/20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/evidence/security-review.md:68`),
i.e. a description of regex families, not a credential.

The `.env.example` values shipped inside the archive were dumped and are all placeholders:
`FACTORY_POSTGRES_PASSWORD=replace-owner-for-local-use`,
`FACTORY_LANDING_*_API_KEY=replace-*-key-for-local-use`,
`TRUST_CI_WEBHOOK_SECRET=REPLACE_WITH_LONG_RANDOM_SECRET`,
`POSTGRES_PASSWORD=REPLACE_WITH_LONG_RANDOM_ADMIN_PASSWORD`, and the two `*.pem` matches
(`TRUST_CI_SIGNING_KEY_PATH=/run/secrets/trust-ci-signing-key.pem`,
`TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app-private-key.pem`) are
filesystem *paths* where an operator must later mount a key, not key material.

**Archived candidate record vs live record (expected, documented — not a defect):**
`adaptive-grok-build-pro/PROJECT_STATE.json` inside the ZIP is the R-era pre-publication
snapshot: `local_candidate.status = "pending_release"`,
`artifact_status = "pending_unpublished_artifact_child"`,
`artifact_child.status = "not_built"`, `source_parent = null`, `source_base =
7bbf42526f207db0007daafa4cc946cc2d81f465`. The live tree says
`artifact_bytes_delivered` / `pending_tag_and_release` / `built_byte_reproducible_twice`.
They therefore **do disagree**, and that disagreement is the correct consequence of
building from the merged parent: the child's record/doc/test bytes cannot be inside an
archive derived from the commit before them. It is disclosed in the record itself
(`zip_source_note`: "…whose bytes are deliberately not part of the archive
(pre-publication snapshot caveat of the v2.0.15 precedent)") and again in
`current_unreleased_change.artifact_child`. Crucially, the archived record claims no
publication either: inside the archive `published=false`, `external_effect=false`,
`operational_activation=false`, `published_at/merge_commit/tree/pull_request/checked_head`
all null, and `published_release` still `v2.0.16` — identical to the live one for those
sections (verified by direct equality compare).

---

## 4. Provenance of the new dossier — only re-pins, no new machine-local or secret value

Key-by-key compare of
`engineering/changes/20260916-…-31155d/evidence/runtime-observation-post-98.json` against
the previous tracked `engineering/changes/20260915-release-sync-…-f98796/evidence/runtime-observation-post-94.json`
found exactly 8 differing leaves:

```
CHANGED /observed_at            2026-09-15T23:02:27Z -> 2026-09-16T00:23:18Z
CHANGED /source_base            7bbf4252… -> 78082a29…
CHANGED /observation_provenance/method              (+ "; repeated from the previous observation")
CHANGED /observation_provenance/previous_dossier    post-91 -> post-94
CHANGED /observation_provenance/unchanged_since_previous/note   (PR list wording)
ADDED   /source_trail/artifact_state                (artifact-delivered disclaimer text)
LEN     /source_trail/merged_source_not_installed   3 -> 1
CHANGED /source_trail/note                          (PR #98 wording)
```

Everything else is byte-identical, including the whole `published_release` block, the
installed release/socket/control paths
(`/opt/adaptive-l5/releases/5f6f6ce…/repository`, `/run/adaptive-l5-grok/control`), the
profile identifier `grok-connect-20260915-61a05da2bd0c`, the carried artifact digests and
both `MainPID` readings. The carried-forward digests are explicitly justified in
`observation_provenance.carried_reason` ("historical acceptance facts … must not be
restated as new evidence"), and `method` still says "read-only, unprivileged".

Live re-verification of the only field this commit can honestly attest (service state),
with the permitted read-only command:

```
$ systemctl show -p MainPID -p Id -p ActiveState -p UnitFileState adaptive-l5.service adaptive-l5-grok.service
MainPID=698333
Id=adaptive-l5.service
ActiveState=active
UnitFileState=enabled

MainPID=3597736
Id=adaptive-l5-grok.service
ActiveState=active
UnitFileState=enabled
```

This reproduces the dossier's `service_observation` verbatim, so the dossier is truthful
right now, and neither unit was restarted by this change. **Conclusion: this commit
introduces no new machine-local identifier, path, digest or secret value — only
`observed_at`/`source_base` re-pins, source-trail wording, and the (unchanged, re-checkable)
systemctl reading.**

---

## 5. Secrets scan of added lines — nothing credential-shaped; all novel tokens resolved

`git diff 78082a2..HEAD -- ':!packages/…zip'` added-line extraction of hex/long-token/email
shapes produced no `@domain` address and no key material. Every novel token resolves:

| Token | Resolution |
| --- | --- |
| `78082a290f8b90cade88685351fbb2ba263689b9` | Git commit; `git show -s` = "docs(release): v2.0.17 candidate identity sync (R) … (#98)", parent `7bbf4252…`, committer date `2026-09-16 03:19:18 +0300`. This is the base. |
| `2283e6a09d3eb2a0aeabce8a872e06746b941176` | `git rev-parse 78082a2^{tree}` — the base tree, independently reproduced by the clone in §1.3. |
| `770f1db5…4616` / `54db9f64…f3c0` | Recomputed ZIP and sidecar SHA-256 (§1.1). |
| `969c4f65f54ef9230f3f94587e228098d1c2ecb9` | v2.0.16 tag target; already public — `git ls-remote` shows `refs/tags/v2.0.16^{} -> 969c4f65…`. |
| `06ecf1c875bc`, `4694114`, `104591923631` | Policy-epoch check-name fragment / App ID / check-run id, pre-existing constants on main (`tests/test_project_state.py` context lines, unchanged). |
| `31155d4d2a6a` | Local route id; `router.py:438` derives it as `sha256(f'{session_id}|{prompt}|{base_fingerprint}').hexdigest()[:12]`. Workflow metadata, not a credential. |
| `e267fd61a28e1cc91b62795ddcaa8a3583086d0a619d1b819d2d9838a4310ed1` | `route.json:base_fingerprint`, produced by `tree_fingerprint(root)` in `.grok-stack/adaptive_grok/router.py:428-432` and asserted by `tests/test_structure.py:76-77`. It is **not** a Git object (`git cat-file -t …` → "fatal: Not a valid object name"); it is the local workflow tree fingerprint for this route. No secret. |
| `698333`, `3597736` | systemd `MainPID` readings, re-confirmed live in §4 and unchanged from the previous dossier. |
| `7bbf42526f207db0007daafa4cc946cc2d81f465` | Previous base, already on main. |

The author address `bpall@mail.ru` appears only in commit metadata (the repo's standing
git identity for every prior commit on main), not in any added file line.

---

## 6. Immutability — frozen records untouched; protected paths empty

Data-level comparison of the two `PROJECT_STATE.json` blobs
(`git show 78082a2:PROJECT_STATE.json` vs the working file), recursive leaf walk:
**18 changed leaves, all enumerated and all expected** — `/observed_at`,
`/observed_main_sha`, `/current_unreleased_change/{artifact_child,source_base,stage}`,
`/local_candidate/{status,artifact_status,source_base,notes}`,
`/local_candidate/artifact_child/{source_parent,source_parent_tree,zip_sha256,sidecar_sha256,status,zip_source_note,requirement}`
and `/runtime_observations/{observed_at,evidence}`. No other key moved.

Canonical-hash comparison of the frozen sections between base and HEAD:

```
published_release            equal=True  ce34ff7eda522c1c / ce34ff7eda522c1c
prior_published_releases     equal=True  3d886b110eda8c9c / 3d886b110eda8c9c
milestones                   equal=True  64a2b675fe0c03da / 64a2b675fe0c03da
operational_qualification    equal=True  5ed3f21df9e6e18d / 5ed3f21df9e6e18d
l5_production_preparation    equal=True  f39b0b61ee610a90 / f39b0b61ee610a90
trust_ci                     equal=True  893081e0be0120ac / 893081e0be0120ac
fresh_clone                  equal=True  1f207df551e91158 / 1f207df551e91158
delivered_change_history     equal=True  ad8ec9592ca30c1c / ad8ec9592ca30c1c
work_inventory / intentionally_untracked / delivered_milestones_on_main /
implemented_milestones / latest_published_release / product_version   equal=True
current_unreleased_change.frozen equal=True
   {"published_release": "v2.0.16", "package_bytes": true, "postgresql_migrations": "001-018"}
```

The frozen PostgreSQL migration range is intact both as an assertion and as bytes: no
`migrations`/`*.sql` path appears in `git diff --name-only 78082a2..HEAD`, and
`factory/src/adaptive_factory/resources/` still lists `001_initial.sql … 018_semantic_validation_bridge.sql`
(with `019`/`020` outside the frozen range, untouched).
`packages/README.md` changed by exactly one insertion and zero deletions
(`git diff --numstat` → `1 0 packages/README.md`), so the v2.0.13–v2.0.16 rows are
byte-identical and only the v2.0.17 row was appended.

Protected-path check:

```
$ git diff --name-only 78082a2..HEAD -- trust-ci architecture governance factory scripts
(empty)
```

The full change set is 23 paths: 2 artifact files, 12 change-package files, 7 docs/state
files (README, START_HERE, GROK_BUILD_HANDOFF, CHANGELOG, DARK_FACTORY_ROADMAP,
PROJECT_STATE.json, packages/README.md) and 2 test files. No packaging code
(`scripts/package_stack.py`), no Trust CI policy, no architecture model, no governance or
factory runtime file was touched, so the commit cannot alter deployed trust policy.

---

## Findings

**Critical: none.**

**Important: none.**

### Minor

1. **Day-label currency lag on the changed observation rows.** README.md:9 keeps the table
   caption "| Layer | Observed state on 2026-09-15 |" while its first row now names
   `78082a29…` (committed `2026-09-16 03:19:18 +0300`, i.e. `00:19:18Z`);
   START_HERE.md:7 keeps "Snapshot: **2026-09-15**." with the same SHA;
   `tests/test_project_state.py:16` comment reads
   `"# 2026-09-15 observation, PR #98 release-sync merge"` while the regex two lines below
   now requires `^2026-09-16T` and `observed_at` is `2026-09-16T00:24:00Z`.
   No false publication claim and no truthfulness failure about the artifact, but the day
   labels contradict the pinned SHA/`observed_at` for a zero-context reader.
   Fix in the post-publication successor `SR` alongside the rest of the date sync —
   the CHANGELOG heading `## 2.0.17 — 2026-09-15 (candidate, unpublished)` must **not** be
   moved by this child (AC-004 identity freeze).
2. **CHANGELOG.md:5 keeps a now-satisfied future clause.** "`v2.0.16` remains the only
   published artifact, and the source below reaches a release archive only once the
   `v2.0.17` artifact child is built from the merged release-sync tree." The first half is
   still true; the second frames the artifact child as pending although this very commit
   delivers it. Not a publication claim (it denies publication), just stale framing —
   reword in `SR`.
3. **GROK_BUILD_HANDOFF.md:304 still names the older observation.** Item 2 under
   "Next actions (observed 2026-09-15)" reads "Source `main` was observed at
   `7bbf42526f207db0007daafa4cc946cc2d81f465`" while item 1 of the same section was updated
   to the delivered-artifact state. The dated heading keeps it from being a false current
   claim, but the section is internally split across two observation days; align in `SR`.
4. **Dossier `merged_source_not_installed` shrank 3 → 1.** The three per-PR entries
   (#93/#13/#94) were collapsed into one note about PR #98. No fact is contradicted (the
   installed SHAs `5f6f6ce1…`/`61a05da2…` are restated and unchanged), but the earlier
   per-PR detail now survives only in the superseded dossier. Acceptable; noted so the
   successor does not treat the list as a growing ledger.
5. **Known local-verification asymmetry is disclosed, not hidden.** The commit message and
   `requirements.md` state that the repository verifier refuses the >10 MB tracked binary
   (issue #80). That weakens *local* automated coverage of this file, which is precisely why
   §1.1–§1.3 of this review re-measured the digest and rebuilt the archive independently.
   Merge authority stays the App-owned exact-head check
   `adaptive-trust-ci/verified@06ecf1c875bc` on the PR head SHA.

---

## Verdict

**PASS** for the security scope of route `31155d4d2a6a`.

- FORBID-002: independently reproduced — a clean detached clone of `78082a2…`
  (tree `2283e6a0…`) built the byte-identical `770f1db5…` / 10,940,676 B archive in `0700`
  staging; tracked bytes, committed blob, record and sidecar all agree, and the sidecar text
  is exactly `<zip-sha>  adaptive-grok-build-pro-v2.0.17.zip\n`.
- FORBID-001: no publication, external effect or activation is claimed anywhere, the child
  self-records nothing, and the remote has no `v2.0.17` tag or Release.
- Archive contents carry no secret, no symlink, no absolute path and are fully prefixed.
- The new dossier re-pins only `observed_at`/`source_base` plus a re-checkable systemctl
  reading; it introduces no new machine-local or secret value, and the service state it
  records is live-true at review time.
- Frozen release, migration, milestone, qualification, Trust CI and prior package rows are
  unchanged at data level; protected paths are empty.

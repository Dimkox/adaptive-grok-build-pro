# repo_explorer: M0.2 SHA-change facts (draft PR #5)

Route: `beee95e0b3c6`. Read-only map. No PEM/.env. No push.

Observed: 2026-08-24. Remote: `https://github.com/Dimkox/adaptive-grok-build-pro.git`.

## 1. SHAs

| Ref | SHA | Note |
| --- | --- | --- |
| Local HEAD (`milestone/m0-live-trust-authority`) | `ca1e88aad3dafcfeb81583f443f67c49c1faeab6` | `ca1e88a ops: record live M0 Check Run and host-local kill-switch drill` |
| `origin/milestone/m0-live-trust-authority` | `1fc942065a124ce75659bd082519d8ebc37774e8` | Local branch **ahead 1** |
| PR #5 head | `1fc942065a124ce75659bd082519d8ebc37774e8` | Draft, open, base `main` @ `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| Check Run `97390635614` `head_sha` | `1fc942065a124ce75659bd082519d8ebc37774e8` | Same as origin / PR head, **not** local HEAD |

`1fc9420` is an ancestor of local HEAD. Unique local commit: `ca1e88a`. PR #5 title still describes worker-not-running / SHA `1fc9420`; body is stale vs live compose.

https://github.com/Dimkox/adaptive-grok-build-pro/pull/5

## 2. Dirty / untracked (belong vs leftover)

Working tree: **not clean**. Nothing staged.

### Belong on this milestone branch (85a17e + M0.2 package)

- `engineering/changes/20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e/state.json` (modified)
- `engineering/changes/20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e/evidence/code-review.md` (untracked)
- `engineering/changes/20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e/evidence/test-review.md` (untracked)
- `engineering/changes/20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95/` (untracked current change package)

85a17e analysis/implementation files already exist under that package; reviews are the new untracked evidence.

### Leftover — do not git-add (9d97f8 / 37bf04 / 33e0c2)

- `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/state.json` (modified, unrelated session)
- `engineering/changes/20260824-user-query-да-user-query-37bf04/` (untracked whole package)
- `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` (untracked whole package)

Also never add: `trust-ci/runtime/*.pem`, `trust-ci/env/*.env` (non-example), `.env`, HMAC helper scripts.

## 3. Live compose + ready

Project: `adaptive-trust-ci` from `trust-ci/compose.yaml` (worker also overlays `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml`).

| Service | Container | State | Health |
| --- | --- | --- | --- |
| api | `adaptive-trust-ci-api-1` | running ~2h | **healthy** (`127.0.0.1:18080->8080`) |
| postgres | `adaptive-trust-ci-postgres-1` | running ~2h | **healthy** (5432 not published) |
| worker | `adaptive-trust-ci-worker-1` | running ~55m | **no HEALTHCHECK** (`health=none`); process is up |

`GET http://127.0.0.1:18080/health/ready` → **HTTP 200**

```json
{"status":"ready","policy_digest":"6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5","status_context":"adaptive-trust-ci/verified","active_approval_keys":1,"status_publisher":"worker-github-app"}
```

Policy SHA12 `6737355947c2` matches Check Run name suffix.

## 4. Check Run 97390635614

| Field | Value |
| --- | --- |
| id | `97390635614` |
| name | `adaptive-trust-ci/verified@6737355947c2` |
| **head_sha** | **`1fc942065a124ce75659bd082519d8ebc37774e8`** (yes, still on `1fc9420`) |
| app.id | `4694114` |
| app.slug / name | `adaptive-trust-ci` / Adaptive Trust CI |
| **external_id** | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` |
| status / conclusion | completed / `action_required` |
| started / completed | 2026-08-24T09:48:09Z / 09:52:05Z |
| details_url | `http://127.0.0.1:18080/jobs/1b63d10b-90c1-498a-97b8-7b5e0ea76aec` |

PR check_runs total_count=2: this Trust CI run + GitGuardian success `97384448347`.

A SHA change (push of `ca1e88a` or later) must **not** reuse this check on `1fc9420`. New head needs a new Check Run bound to the new SHA.

## 5. HMAC leftover helper

- `/tmp/m0-hmac-pr5.py`: **does not exist**
- No `/tmp/*.py` matching hmac
- `/tmp` M0-named leftovers (not HMAC, names only): `m0-health.out`, `m0-invariant-manifest.json`, `m0-own.sh`, `m0-stop.sh`

## After push — SHAs to compare

1. Local `HEAD` (today `ca1e88aa…`; after extra commits, the new tip).
2. `origin/milestone/m0-live-trust-authority` (must equal local HEAD if push succeeded).
3. PR #5 `head.sha` (must equal origin tip; currently `1fc9420`).
4. New Check Run `head_sha` (must equal PR head; **must differ from** `97390635614` / `1fc9420`).
5. Old run `97390635614` should remain on `1fc9420` (stale for the new tip).

## Files that must NOT be git-added

- `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/state.json`
- `engineering/changes/20260824-user-query-да-user-query-37bf04/` (entire tree)
- `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` (entire tree)
- `trust-ci/runtime/*.pem`, `trust-ci/env/*.env` (except `*.example`), `.env`, credentials
- Any HMAC helper script (none present under `/tmp/m0-hmac-pr5.py`)

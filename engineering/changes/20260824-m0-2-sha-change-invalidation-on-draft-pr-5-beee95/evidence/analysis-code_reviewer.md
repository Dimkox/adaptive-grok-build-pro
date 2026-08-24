# Pre-implementation analysis: SHA-change invalidation vs Check Run reuse

**Agent:** `code_reviewer` (read-only; not a post-implementation review of a product diff).  
**Route:** `beee95e0b3c6`  
**Change:** `engineering/changes/20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`  
**Question:** Does a new PR head SHA create a new durable job and a new GitHub Check Run, or can Check Run `97390635614` on SHA `1fc9420` be reused?

**Verdict:** A **new head SHA creates a new job** (new `job_id` / new idempotency key). The worker lists Check Runs **only on that SHA** and reuses a run only when `external_id == job_id`. Therefore **97390635614 on 1fc9420 cannot be reused** for a later SHA. The old durable job is cancelled with `failure_code=superseded-head`; **GitHub is not PATCHed to cancelled** for that old Check Run.

---

## 1. Idempotency includes `head_sha` — new SHA ⇒ new job

`JobRequest.idempotency_key` hashes `repository`, `pr_number`, **`head_sha`**, `pipeline`, `policy_digest`:

```77:89:trust-ci/src/adaptive_trust_ci/models.py
    def idempotency_key(self, policy_digest: str) -> str:
        digest = require_digest(policy_digest, "policy_digest")
        return hashlib.sha256(
            canonical_json(
                {
                    "repository": self.repository,
                    "pr_number": self.pr_number,
                    "head_sha": self.head_sha,
                    "pipeline": self.pipeline,
                    "policy_digest": digest,
                }
            )
        ).hexdigest()
```

Replaying the **same** SHA + policy returns the existing job (`created=False`). A **different** SHA cannot hit that key.

Memory store: lookup by key first; miss ⇒ new UUID job.

```49:92:trust-ci/src/adaptive_trust_ci/store.py
    def enqueue(...):
        with self._lock:
            key = request.idempotency_key(policy_digest)
            existing_id = self._idempotency.get(key)
            if existing_id:
                return copy.deepcopy(self._jobs[existing_id]), False
            ...
            job = Job(
                job_id=str(uuid.uuid4()),
                ...
                head_sha=request.head_sha,
                ...
                idempotency_key=key,
```

Postgres: `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`; conflict reloads the row (`created=False`). New SHA inserts a new row.

```297:353:trust-ci/src/adaptive_trust_ci/store.py
    def enqueue(...):
        key = request.idempotency_key(policy_digest)
        ...
                INSERT INTO trust_ci_jobs (
                    job_id, repository, pr_number, base_sha, head_sha, ...
                    pipeline, policy_digest, idempotency_key, status, ...
                ) VALUES (... 'queued' ...)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING *
        ...
            created = row is not None
            if row is None:
                cursor.execute("SELECT * FROM trust_ci_jobs WHERE idempotency_key = %s", (key,))
```

Covered by `StoreTests.test_enqueue_is_idempotent_for_same_sha_and_policy` (`trust-ci/tests/test_store.py:27-32`).

**HMAC of SHA `1fc9420`:** same key as the existing job → `created: false`, **no new job**. Invalidation proof requires a **different** head SHA.

---

## 2. Superseded-head cancellation (durable job only)

On enqueue of a **different** `head_sha` for the same repo/PR, active jobs (`queued|leased|running|needs_approval`) are cancelled with `failure_code='superseded-head'`.

Memory (`store.py:62-74`):

```
for job in self._jobs.values():
    if (
        job.repository == request.repository
        and job.pr_number == request.pr_number
        and job.head_sha != request.head_sha
        and job.status in {"queued", "leased", "running", "needs_approval"}
    ):
        job.status = "cancelled"
        job.failure_code = "superseded-head"
```

Postgres (`store.py:307-317`):

```
UPDATE trust_ci_jobs
SET status = 'cancelled', failure_code = 'superseded-head',
    lease_owner = NULL, lease_expires_at = NULL,
    updated_at = %s, finished_at = %s
WHERE repository = %s AND pr_number = %s AND head_sha <> %s
  AND status IN ('queued', 'leased', 'running', 'needs_approval')
```

Test: `test_new_head_cancels_old_active_job` (`test_store.py:34-46`) — first job `cancelled`, second `queued`.

**Gap vs GitHub:** neither `MemoryStore.enqueue` nor `PostgresStore.enqueue` calls `GitHubClient`. There is **no** `complete_check_run(..., conclusion='cancelled')` on enqueue. Check Run `97390635614` can remain `in_progress`/`completed` on `1fc9420` while the durable job is `cancelled`.

`JobRunner.process` / `publish_dead_job` complete checks for **the job being processed**, not for superseded siblings (`runner.py:53-60`, `280-298`). A cancelled queued job never gets a worker complete.

---

## 3. `ensure_check_run` — list **this SHA**, match `external_id=job_id`

```130:184:trust-ci/src/adaptive_trust_ci/github.py
    def ensure_check_run(
        self,
        repository: str,
        sha: str,
        *,
        name: str,
        external_id: str,
        ...
    ) -> int:
        """Create one App-owned Check Run per durable job, or reuse it after retry."""
        encoded_name = urllib.parse.quote(name, safe='')
        existing = self._request(
            'GET',
            f'/repos/{repository}/commits/{sha}/check-runs?check_name={encoded_name}&filter=latest&per_page=100',
        )
        ...
                for run in runs:
                    if (
                        isinstance(run, dict)
                        and run.get('external_id') == external_id
                        and isinstance(run.get('id'), int)
                    ):
                        check_run_id = int(run['id'])
                        self._request('PATCH', f'/repos/{repository}/check-runs/{check_run_id}', ...)
                        return check_run_id
        created = self._request(
            'POST',
            f'/repos/{repository}/check-runs',
            {
                'name': name,
                'head_sha': sha,
                ...
                'external_id': external_id,
```

Worker passes **job.head_sha** and **job.job_id**:

```53:59:trust-ci/src/adaptive_trust_ci/runner.py
        check_run_id = self.github.ensure_check_run(
            job.repository,
            job.head_sha,
            name=self.policy.check_name,
            external_id=job.job_id,
            details_url=target_url,
            started_at=job.started_at or started_at,
        )
```

Reuse conditions (all must hold):

| Condition | New-SHA job |
| --- | --- |
| GET `/commits/{sha}/check-runs` | `sha` is the **new** head, not `1fc9420` |
| `external_id == job_id` | New UUID ≠ old job that owned `97390635614` |

Even if GitHub listed the old run (it does not — Checks API is commit-scoped), the `external_id` would not match.

POST body always sets `head_sha` to the **current** job SHA (`github.py:175`). Tests:

- `test_create_check_run_uses_installation_token_exact_sha_and_external_id` — empty list → POST; `body['head_sha']` and `external_id` (`test_webhooks_github.py:80-112`).
- `test_existing_check_run_is_restarted_instead_of_duplicated` — same SHA + same `external_id` → PATCH, no POST (`test_webhooks_github.py:114-135`). That is **retry of the same job**, not a SHA change.

---

## 4. Mapping to Check Run 97390635614 / SHA 1fc9420

| Event | Durable store | GitHub Checks |
| --- | --- | --- |
| HMAC / webhook with `head.sha=1fc9420` (same policy) | Idempotent: same job, `created=false` | Worker may PATCH 97390635614 if still matching `external_id` **on 1fc9420** |
| Webhook with **new** `head.sha` | Cancel old job `superseded-head`; INSERT new `job_id` | GET checks on **new** SHA; no match; **POST new Check Run** bound to new SHA + new `external_id` |
| Old Check Run 97390635614 | Job cancelled in DB only | **Not reused**; not auto-cancelled by enqueue |

Do **not** implement PATCH of 97390635614 to `cancelled` as part of this slice unless a later contract explicitly requires GitHub-side unpublish.

---

## 5. Residual risks (existing code, not a new diff)

1. **Stale Check Run on old SHA:** GitHub UI can still show 97390635614 on `1fc9420` after supersede. Branch protection evaluates the **current** head SHA, so the new run is what matters if required checks are SHA-bound.
2. **Postgres enqueue order:** cancel-then-insert is one transaction (`store.py:306-353`). Concurrent workers: same-SHA conflict is `ON CONFLICT DO NOTHING`; different-SHA both cancel then insert two jobs — expected (two SHAs).
3. **List pagination:** `per_page=100`, `filter=latest`. Retry reuse only needs the latest matching `external_id` on that SHA. SHA-change path does not depend on finding the old run.
4. **No GitHub call from store:** API process that only `enqueue`s will not touch Checks; only the worker `JobRunner` creates/completes runs.

---

## 6. Implication for this change package

Existing Trust CI already implements SHA-change **job** invalidation. Observing a **new Check Run id** requires: (1) a **new** PR head SHA, (2) worker `process` of the new job. HMAC of `1fc9420` will not produce a new Check Run. Product docs that still name `97390635614` as the *current* check on a later SHA are stale **after** the new job completes; they are not evidence that the code reused that run.

No secrets inspected. No push/merge/deploy.

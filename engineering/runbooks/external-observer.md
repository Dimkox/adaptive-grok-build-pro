# External Observer v1 runbook

The External Observer is a separate, nonprivileged, read-only operator process. It has no controller, Factory, Trust CI, approval, signing, merge, release or production authority.

## Prepare

Copy `engineering/external-observer/external-observer.example.json` outside the repository, replace every placeholder with the one operator-selected repository/default branch/current PR/check-name/App-ID tuple, and create a closed evidence manifest from `engineering/external-observer/historical-evidence.example.json`. Do not commit the live configuration, mutable PR selection, credentials or generated status.

`engineering/external-observer/historical-milestone-claims.v1.json` is a typed inventory of repository claims M0-M9. Its `historical_evidence_claimed` value means only that historical/project material makes a claim; it does not assert implementation, review, delivery, release or activation.

V1 uses anonymous public GitHub API reads. Anonymous quota is not enterprise-reliable: 403/429 yields `UNAVAILABLE` on the first run and `STALE` after a successful cached projection. A future Observer-only read credential/App with metadata, contents, pull-requests and checks read access requires a separate security review; never reuse the Trust CI checks-write identity.

## Run

```bash
python3 scripts/grok_observer.py observe --config /operator/external-observer.json --evidence /operator/historical-evidence.json
python3 scripts/grok_observer.py status
python3 scripts/grok_observer.py render
python3 scripts/grok_observer.py verify-state
```

Runtime state is written atomically under ignored `.grok-stack/runtime/external-observer/` while holding a no-follow advisory lock. Keep the working directory operator-owned and non-world-writable. The process only performs allowlisted `GET` requests to `https://api.github.com/repos/<configured-repository>/...`; it never follows a Check Run `details_url`.

## Interpret and rollback

`EVIDENCE_CLAIMED` and `historical_evidence_claimed` are claims, not delivery proof. Check success remains distinct from `ATTESTATION_UNOBSERVABLE`; the current loopback/bearer-protected Trust CI job/attestation endpoint is deliberately not followed.

Read `main_sha`, `current_delivery_pr`, `pr_head_sha`, `reviewed_sha`, `trust_ci_sha`/`trust_ci_verdict`, `release_sha` and `evidence_freshness` independently. A stale local PROJECT_STATE or receipt does not erase a live failed/pending Check observation, and no axis implies another.

Rollback is to stop invoking the source-only CLI and retain the last status as stale evidence. Remove only the exact ignored observer runtime directory after preserving it if local audit needs it; no repository, GitHub or Trust CI rollback is performed.

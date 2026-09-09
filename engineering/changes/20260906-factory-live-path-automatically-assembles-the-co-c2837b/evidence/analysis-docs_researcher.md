# Docs research — live L5 vs working landing vs grants

Sources: `origin/main` (`fd51dcfed6b33f4a8707c0db602328146df17cc9`) and `origin/docs/v2.0.15-published-handoff` (`ef7c8faeb5d339c5b4343de61162ea611c130c4d`). No APIs invented.

## What “live L5” is not

Docs never use the phrase “live L5” as an operational hosted site. They use **L5** for an **offline / Stage 3/5 local** factory landing pipeline, and **`--live`** only for the **design-partner pilot CLI** (explicit operator flag, still grant-gated for GitHub writes).

`origin/main` `START_HERE.md` item 6:

- Treat L5 as **published repository capability plus a distinct unreleased Stage 3/5 single-operator local runtime, not an operational site**.
- Exact landing source clone stays **read-only**.
- Provider and publisher **defaults stay unavailable**.
- **Live model use, cPanel, hosting, production and other external effects require separate evidence and authority.**

`origin/docs/v2.0.15-published-handoff` `START_HERE.md` item 6 (wording delta only):

- Treat **L5 and the v2.0.15 pilot as published repository capability at pre-pilot Stage 3/5, not an operational site**.
- Same read-only clone, unavailable defaults, and grant/evidence requirement for live model / cPanel / hosting / production.

Same file on both refs: L5 is **not** “live/indexed-site”; that still needs separate evidence (`START_HERE.md` PR #24 / `v2.0.14` bullet).

## What a “working landing” means in-repo (automatic assembly)

This is **local artifact construction**, not hosting.

### Factory README (`factory/README.md`, identical on both refs)

Title: “offline L5 landing source”.

Published `v2.0.14`: L5 landing state/store + four authenticated routes (intake, status, cancellation, **local artifact results**).

Unreleased Stage 3/5 local runtime:

- Pinned source `Dimkox/ai-dark-factory-landing@699010380f4f90a0193a9c22090c35e6aded7d2c` / tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
- Protected source-owned `index.css`.
- **20-member deploy inventory**.
- Renderer writes only `index.html` / `content.css`.
- Default-unavailable native-Codex normalizer seam.
- Private SQLite replay/recovery.
- **Concrete coordinator-to-packager artifact builder**.
- PDF/audio stop at `needs_human`.
- Publisher has **no transport**; **every result `live_url` null**.
- **No live model, target mutation, deployment, publication, or indexing claimed.**

Factory README also: the package **does not** make a live provider call, GitHub write, deploy, or publish.

### Root README (`README.md` on `origin/main`)

`v2.0.14` L5: bounded multimodal intake → at most three exact-SHA candidates → **deterministic site artifact** (text there still says **19-member**; later repair packages document **20-member** after adding `index.css`). Publisher: no transport, `live_url` always null. Publication did not host or index.

### L5 change packages (on both refs)

1. `engineering/changes/20260904-l5-multimodal-landing-dogfood-9f67ef/`
   - Closed intake → `StaticLandingSpecV1` → trusted renderer → independent eval (≤3 attempts) → **deterministic ZIP + sidecar**.
   - **REQ-009 / architecture:** publisher protocol exists but **unavailable**; **deny before transport**; never a live URL; no `live` / `https_observed` / `indexed_observed`.
   - Production blocked until separate provider/hosting/TLS/M8/M9 **and explicit external action grants**.

2. `engineering/changes/20260904-repair-l5-current-landing-source-binding-eb3f80/`
   - Current working source binding: SHA/tree above; **complete 20-member site artifact**; writes still only `index.html`/`content.css`.
   - Out of scope: provider execution, durable job runtime, **cPanel/LiteSpeed**, live deploy, DNS, indexing, credentials, **target mutation**.

3. `engineering/changes/20260905-l5-single-operator-live-mvp-local-runtime-65b201/`
   - “Live MVP” here means **offline technical preview**: fake/unavailable executor + SQLite + **`CoordinatedLandingArtifactBuilder`** composing existing coordinator/evaluator/packager into **`SiteArtifactV1`**.
   - Outcome: `live_url` remains `null`.
   - Out of scope: any live Codex/model call, network, hosting mutation, GitHub, publication, deployment; **cPanel is downstream and grant-gated**.
   - FORBID-004: do not report a live URL or claim operational L5/cPanel/hosting/model/production.
   - Architecture: interrupted work is **not automatically replayed**; no automatic external effect on recovery.

**In-repo automatic assembly** = normalize (when profile allows) + render + evaluate + pack **`SiteArtifactV1` / ZIP+sidecar** locally. That is the “fully assembled лендос” the factory is allowed to do without a grant.

## Grant-gated: model, push, host

### Design-partner pilot runbook (identical on both refs)

Path: `engineering/runbooks/design-partner-pilot-v2.0.15.md`

- Describes a **capability**; **grants no permission** to invoke Codex, push, PR, merge, release, deploy, or read credentials.
- CLI **unavailable by default**. **Without `--live`, every effect-capable command returns `live_disabled`.** `status` is read-only.
- **No automatic model, test, or write retry.**
- Frozen target: same SHA/tree as L5 repair; issue `#1`; exact path list; protected `index.css`.
- **Live precondition unmet:** observed landing `main` `80d621545938e24c296420d7f685f2d0b2b5785e` — frozen profile **stops before model execution** on mismatch (`START_HERE.md` / runbook).
- Phases (each a **separate finite operator command**):
  1. `--live prepare` — one Codex start + seal/validate; **no GitHub write**. Needs separate authority for the provider attempt.
  2. Stop → **new grant** `git-push-branch` + exact resource digest → `--live publish-branch` (at most one non-force push).
  3. Stop → **new grant** `external-write` / `pull-request-create` → `--live publish-proposal` (one draft PR). **No merge, deploy, release, host.**
- Branch grant **cannot** authorize a proposal. Wildcard/stale grants fail closed.
- Rollback: omit `--live`; do **not** automatically delete/overwrite branch/PR.

`delivery/src/adaptive_delivery/landing_publisher.py` (`origin/main`): only `UnavailableLandingPublisher`; `publish` always raises `publication_unavailable`. No transport.

`DARK_FACTORY_ROADMAP.md` L5 row: operational provider, data transfer, target write, signing, **hosting** and production **require separate authority**.

## Split for implementers

| Automatic in factory (no grant) | Grant / separate authority |
| --- | --- |
| Closed intake, spec, render `index.html`+`content.css`, ≤3 eval attempts, pack 20-member `SiteArtifactV1`, SQLite replay of **local** jobs | Native Codex / live model (`--live prepare`, closed host config) |
| Default `provider_unavailable`; PDF/audio `needs_human` | GitHub push / draft PR (`grok_approve.py` exact action+resource) |
| `live_url` always null; publisher deny-before-transport | Hosting, cPanel, TLS, indexing, production, merge, deploy |

Do not treat “live factory” as auto-host or auto-push. Docs: **assemble the landing artifact automatically; keep model/push/host grant-gated and default-off.**

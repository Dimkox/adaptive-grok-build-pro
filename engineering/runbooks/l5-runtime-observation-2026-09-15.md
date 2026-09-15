# L5 runtime observation — 2026-09-15

This is a dated operational observation, not an instruction to install, publish or call a provider. Sanitized facts are retained in the [observation record](../changes/20260915-documentation-align-readme-roadmap-and-bootstrap-d7264b/evidence/observed-state.json) and projected into [PROJECT_STATE.json](../../PROJECT_STATE.json).

## Source, release and installed services

At `2026-09-15T09:54:21Z`, source `main` was `61a05da2bd0c9fb09db5307f53ebc99e4e94040d`. The latest published release remains [`v2.0.16`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.16), published `2026-09-13T22:04:08Z`, targeting `969c4f65f54ef9230f3f94587e228098d1c2ecb9`. Post-release source and installed releases need not equal that immutable tag.

| Role on Claw | Unit | Installed source SHA | Observed service state |
| --- | --- | --- | --- |
| Qwen primary | `adaptive-l5.service` | `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` | active, enabled |
| Grok secondary | `adaptive-l5-grok.service` | `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` | active, enabled |

The primary instance selects `qwen-intl` / `qwen-plus`, with its control checkout at `/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/repository`. The secondary selects `grok-vision` / `grok-4.6`. The source template independently selects Qwen Omni. Repository defaults remain `live_enabled=false`; these explicitly enabled instances have their own installed-state evidence. The documented installer's creation of default-off release files is separate from operator provisioning and systemd activation.

## Authenticated artifact results

- Qwen: the saved observation at `2026-09-14T03:31:08+00:00` records the PR #82 installed SHA, successful normalization and an authenticated Unix request `pr82-smoke-5f6f6ce1ecb0`. A transient acceptance unit using that installed release reached `artifact_ready`, exit `0`, elapsed service time `10.314 s`, artifact digest `85b3360aaa28c38448c8d31770a5307df809aa7ce4829e81f1ac7b4ddddc76ed`, `live_url=null`.
- Grok: [PR #88](https://github.com/Dimkox/adaptive-grok-build-pro/pull/88) source was installed for the secondary service. Authenticated job `grok-connect-20260915-61a05da2bd0c` returned HTTP `202` and reached `artifact_ready` in **29.852 s**, with **one provider request**, artifact digest `90865bde1fa3171c2a5f84bb92a18fdfde514451c659ddf26282ed8e1fed66b2`, `live_url=null`. Its source PR checked head `4e94f7a9e0b6a54adac5e09700ba3137a1c2e6b0` has App-owned check `104295309671` and attestation `8a7eb170-fd21-481e-a756-9e0a878b14c0`; source acceptance and runtime acceptance are separate records.

The September 15 service observation is a read-only status check. This documentation correction made no additional live model request. Detailed credentials, service config, private runtime state and raw inputs remain outside Git.

## Evidence limits and next outcomes

These results establish bounded authenticated L5 artifact generation on two exact installed source revisions. They do not establish acceptance of every supported media class, a full external issue-to-proposal pilot with maintainer acceptance, an M8 exact-profile qualifying cohort/activation, or general M9 environment/recovery qualification.

Complete pilot cost and human-intervention accounting remain unestablished. One successful artifact and one provider-request count do not establish accepted-tasks-per-euro economics. `live_url=null` and these jobs provide no factory publication evidence; an independently hosted public landing is a separate deployment and must not be overwritten with a synthetic acceptance artifact.

Continue with the externally accepted pilot outcome and its factual accounting, then assess M8/M9 gates in the [roadmap](../../DARK_FACTORY_ROADMAP.md). New source or runtime changes need fresh exact-state evidence and the applicable authority; a dated success is not perpetual readiness or permission.

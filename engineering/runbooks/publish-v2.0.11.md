# Publish v2.0.11 — Historical record

This file is a **Historical record** of a release completed before the protected trust boundary was introduced. The former local tag, push, release, and rollback commands are retired and must not be reused.

Current delivery and publication are defined in [`docs/TRUST-BOUNDARY.md`](../../docs/TRUST-BOUNDARY.md):

```text
feature branch
→ pull request
→ exact-SHA trusted CI
→ CODEOWNER approval
→ protected merge
→ production Environment approval
→ exact-SHA release workflow
```

For release facts about v2.0.11, use the Git tag, GitHub Release metadata, and `CHANGELOG.md`. Do not recover operational commands from older commits.

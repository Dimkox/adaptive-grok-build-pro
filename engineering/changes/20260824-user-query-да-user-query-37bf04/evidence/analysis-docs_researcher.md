# Docs: bootstrap merge recipe (PR #2 → reuse for PR #4)

Sources: `decisions.md` 2026-08-23 bootstrap; `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/evidence/analysis-architect-release.md` §3–4; `CHANGELOG.md` 2.0.12; `AGENTS.md` (no GHA, no forge check).

**Grant resource** is the **PR URL**, not the SHA. Merge tool is **Bash `gh pr merge`**. MCP `github__merge_pull_request` is **not** `pull-request-merge` (needs `external-write` on the MCP name — do not use it).

**Method = rebase.** `main` has no merge commits; future `required_linear_history` would reject `--merge`. `--squash` collapses Trust CI history — forbidden. Architect: if GitHub **rejects rebase** (allow_rebase_merge off / pathspec), **STOP** — do not fall back to squash/merge-commit. Preflight: `gh pr ready N` (drafts cannot merge). GitGuardian is not Trust CI; do not wait; do not `--admin` while `main` is unprotected.

**Never:** forge `adaptive-trust-ci/verified@*`; `git push origin main`; `.github/workflows/` / GitHub Actions; `compose up` / `branch-protect`; MCP merge.

Copy-paste for PR #4 (head `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4`):

```bash
python3 scripts/grok_approve.py production \
  --action pull-request-merge \
  --resource https://github.com/Dimkox/adaptive-grok-build-pro/pull/4 \
  --source explicit-user-consent \
  --ttl 15 \
  --reason "user ordered merge of PR #4 as bootstrap without live Trust CI check"

gh pr ready 4
gh pr merge 4 --rebase
```

Docs_researcher does not run these. Confirm `headRefOid` still `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` before merge.

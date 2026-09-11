# architect — binding ruling for «да» / PR #4

Route `37bf040834dc`. Change `20260824-user-query-да-user-query-37bf04`. Read-only except this report. No `.env`, keys, push, merge, or deploy.

## Ruling

1. **YES — merge PR #4 now as a named bootstrap exception.** Rebase-merge https://github.com/Dimkox/adaptive-grok-build-pro/pull/4 at exact head `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` onto unprotected `main`. Do not invent `adaptive-trust-ci/verified@*`. Do not protect `main`.
2. **YES — must NOT start M2 or M0 deploy in this operational turn.** Merge #4 only. No Trust CI host bring-up, no `compose up`, no `branch-protect`, no M2 architecture model, no VERSION/tag/release.
3. **Grant:** mint only after the last local write. Scope `production`, action `pull-request-merge`, resource = PR URL (not the SHA), source `explicit-user-consent`, bound to Git HEAD `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` and the then-current tree fingerprint. If HEAD moved, STOP.

```bash
python3 scripts/grok_approve.py production \
  --action pull-request-merge \
  --resource https://github.com/Dimkox/adaptive-grok-build-pro/pull/4 \
  --source explicit-user-consent \
  --ttl 15 \
  --reason "named bootstrap exception: merge PR #4 at 5a63d1c without App-owned check (v2.0.12 precedent); user да"

gh pr ready 4
gh pr merge 4 --rebase
```

Use Bash `gh pr merge`, not MCP `github__merge_pull_request`. Confirm `headRefOid` is still `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` immediately before merge. If GitHub refuses rebase, STOP — no `--squash`, merge-commit, or `--admin`.

## Why (≤10 lines)

User-approved scope is source of truth #1. Parent offered (1) live Trust CI then merge vs (2) explicit merge without App-check like v2.0.12; «да» is the merge order for option 2 because option 1 is still host-blocked (PR #4 has only GitGuardian; combined status pending / 0 statuses; no App-owned policy-epoch check; `main.protected=false`). The 2026-08-23 M0 exception authorized **M1 start and opening this PR**, not merge; this «да» is a new named exception of the same class as PR #2 / v2.0.12, recorded here, not as a forged check. Product SHA is frozen: local `milestone/m1-typed-intent` equals PR head `5a63d1c`; M1 package `5a2a54` is `ready`; leftover dirty paths are change-package paperwork and must not be committed. M0 deploy and M2 are different milestones, credential-bearing / new product surfaces, and outside this grant — splitting them is the roadmap rule (`DARK_FACTORY_ROADMAP.md` M0 vs M1; M2 only after live proof or a recorded exception, and this exception is merge-only). No product files this turn → skip `grok_verify` and the review wave (`AGENTS.md` skip no-op). Post-merge, a later paperwork PR may add a `decisions.md` line; do not rewrite `5a63d1c` to land it.

## Forbidden in this turn

- Forge or wait on `adaptive-trust-ci/verified@*`
- Protect `main`; GitHub Actions; `git push origin main`
- M0 deploy / holdout / pin.env / `compose up` / `branch-protect`
- Start M2–M9; bump VERSION; tag; GitHub Release
- Commit leftover `engineering/changes/20260817-*` or `9d97f8/state.json` or this evidence into the merge
- MCP merge; wildcard grant; `--profile release` (omits `pull-request-merge` and would not bind the PR URL)

M0 live Trust Authority remains open after merge. This exception does not satisfy M0 exit criteria.

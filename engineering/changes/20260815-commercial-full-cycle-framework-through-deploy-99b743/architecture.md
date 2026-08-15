# Architecture — Commercial 2.0.4 through prepare-only deploy

## Decisions

1. **Finish 2.0.4, do not open 2.1.0.** `VERSION` stays `2.0.4`.
2. **`scripts/grok_deploy.py` is prepare-only.** Default dry-run: validate route + current evidence + change status `ready`/`released`; print human commands; no receipt. `--record` requires `has_valid_approval(..., 'production')` and writes receipt kind `deploy` / status `prepared`. Never subprocess `git push`, `gh pr merge`, `gh release create`, `docker push`, `npm publish`.
3. **No new skill.** Extend `release-readiness` to point at `grok_deploy.py`. `adaptive-delivery` close stays “do not deploy”; add one sentence that last mile is `grok_deploy.py`.
4. **CI:** copy template to `.github/workflows/adaptive-grok.yml`. Add a conditional `package` job (`if: hashFiles('scripts/package_stack.py')`). No publish job.
5. **Docs:** README cycle + `engineering/runbooks/publish-v2.0.4.md`. `packages/` is not updated as “published” until the later human gate.

## Target cycle

```
route → change → scope gate → one writer → verify → reviews → ready
  → grok_deploy.py [--record]
  → STOP
human later: grok_approve production → printed tag/push/gh release
```

## Must not change

Production invocation matcher, fail-open Stop, rematch, unwrap, silent SubagentStop, VERSION, Bitrix/secret/destructive gates.

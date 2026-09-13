# Security review — `eb9df64..4e71afa` (#60 derived invariant, #61 prohibited-member guard, #63 worker tests)

## Verdict: PASS — no Critical; 4 Suggestions, 1 Nice-to-have

## Checked and clean
1. **No secrets / private paths.** Grepped the patch itself for `sk-[A-Za-z0-9]{16,}`, `LTAI`, `ghp_`,
   `github_pat_`, `-----BEGIN`, `eyJ`, `AKIA`, `xoxb`, `Bearer`, `password|secret|token|api_key|private_key`, IPv4,
   e-mail domains, `http(s)://`, `/home/`, `/root/`, `/etc/` → **0 hits**. All 90 long opaque tokens are 40-hex git
   ids (already-public epoch shas/trees) + 1 64-hex digest + `/BaseFont/Helvetica`; no `.env`; zero `/home/pall`,
   so the `engineering/**` home-path precedent is never invoked — nothing to grade.
2. **Epoch coverage is complete.** All three `return`s in `deploy_members_for_source` are wrapped and the only other
   exit is `raise …("source_identity")`. `_PRIOR_DEPLOY_MEMBERS` is a *subtractive* filter over `DEPLOY_MEMBERS`, so
   it cannot add a prohibited member and both derivations pass. Other member-list consumers are covered transitively
   by the import self-check (`landing_runtime.py:143/172`, `_write_zip` at `:813`, `seal()`), and
   `landing_artifact_retention.py:223` re-runs the guard on every `validate()`; the zip only ever contains
   `DEPLOY_MEMBERS`, so no prohibited file can reach the deploy root.
3. **No leak in the message.** Emits only `sorted(PROHIBITED ∩ members)` names drawn from module constants — never
   content/size/path/caller input, so no attacker-controlled echo; HTTP discards it anyway
   (`landing_sqlite_store.py:705` → `artifact_integrity`, 500, fixed body `"landing artifact invalid"`).
4. **Worker tests are clean.** Spawn unchanged (`landing_media.py:62-66`): `env` = `PATH=/usr/bin:/bin`, `LANG`,
   `LC_ALL` only — no parent-env/token inheritance; `cwd="/"`, `-B -I`, `close_fds`, `start_new_session`, 20 s
   deadline, 128 KiB cap; child sets `FSIZE=0`,`CORE=0`,`NPROC=1`,`AS=512MiB` before touching bytes. The new test
   writes nothing (in-memory `BytesIO`), uses no tmp, opens no sockets. Ran both modules: 9/9 OK; OK.

## Findings
- **[Suggestion] Exact-name matching misses nested prohibited paths** (`landing_artifact.py:83-87`). Probe:
  `DEPLOY_MEMBERS + ("docs/hidden.md",)` returns **without raising** and `_write_zip` would ship it. The five bare
  dir names (`dist`,`docs`,`reports`,`research`,`tests`) are near-dead for git inventories (`ls-tree -r` yields blob
  paths, never bare `docs`) — they only fire on hand-written tuples. Fix: intersect on
  `PurePosixPath(m).parts[0]` so a dir name blocks its subtree; #61's class is only partially closed.
- **[Suggestion] The test oracle is now circular, so the guard can be weakened silently.**
  `test_landing_artifact.py:39` replaced the independent literal with `PROHIBITED_MEMBERS = PROHIBITED_DEPLOY_MEMBERS`,
  and the new disjointness test compares epochs against that same import. Probe: shrinking the frozenset to one
  element lets prohibited members through with CI green — the source-level equivalent of deleting a line, i.e.
  reopening #61. Fix: keep a hard-coded *floor* (`assertTrue(PROHIBITED_DEPLOY_MEMBERS >= {the 8 names})`).
- **[Suggestion] Enforcement is per-call-site, not structural.** The self-check validates only `DEPLOY_MEMBERS`; a
  future 4th epoch branch written without the wrapper is uncaught (the disjointness test enumerates tuples, not the
  resolver's outputs). Fix: one `dict[(sha,tree)] -> tuple` table with a single wrapped exit.
- **[Suggestion] #60 traded exactness for a floor that can absorb a retirement.**
  `assertEqual(len(records), 41)` → `assertGreaterEqual(…, 41)` + set-equality vs `snapshot.system["contracts"]`; both
  sides are PR-editable, so only the count floor binds: drop one contract, add two → 42 passes, contradicting the
  inline "never retire one silently". Fix: assert retired ids against the merge-base inventory.
- **[Nice-to-have] "Real worker execution" is interpreter-conditional and skips silently.** Without `pypdf==6.18.1`
  (`factory/pyproject.toml:9`) my run reported `OK (skipped=4)`: only `pdf_parser_unavailable` executed the child —
  the text/page-limit/corrupt/blank assertions never ran. Green ≠ executed; mark pin-dependent skips `NOT_RUN`.

## Fail-closed vs fail-open — explicit answer
**Fail-closed is correct; keep it.** `_approved_deploy_members(DEPLOY_MEMBERS)` at `:120` raises at import, and the
module sits under `landing_runtime` → `landing_server` → `server.py`/`landing_host.py`, so a bad edit stops the
**whole control plane**, not just landing — real DoS amplification. But it is reachable only by editing product source
(exactly what the guard exists for, and what the attestation/PR gate binds), and the operator gets one unambiguous
startup error instead of a silently poisoned deploy; fail-open is what allowed #61. Asymmetry: *removing* an entry
from `PROHIBITED_DEPLOY_MEMBERS` is undetectable at import — the floor assertion above restores fail-closed there.

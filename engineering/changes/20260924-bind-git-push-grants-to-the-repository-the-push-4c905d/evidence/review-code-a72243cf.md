# Code review — issue #58 git-push grant repository binding

Reviewer role: code_reviewer (read-only except this report).
Candidate: `/home/pall/grok-projects/adaptive-grok-build-pol58`
Branch observed: `fix/issue-58-installed-policy-cli`
HEAD observed before and after probes: `a72243cf78cd0b49a8105164a0d287cb2940ff4f`
Commit subject: `fix(#58): close push parser review escapes`
`HEAD^{tree}`: `6c6657f9d7d041dbe4f39828877bb61492a37949` (unchanged)
Merge-base with `origin/main`: `5713b407818dbb6c2d1acfcb0b0d9661c32e1153`

reviewed-tree-modified: no

This review did not edit product code, did not commit, and did not push. `git status --porcelain=v1` at the start listed only the pre-existing untracked note `engineering/changes/20260924-bind-git-push-grants-to-the-repository-the-push-4c905d/evidence/next-gap.md`. After the probes, a parallel test review had also added `engineering/changes/20260924-bind-git-push-grants-to-the-repository-the-push-4c905d/evidence/review-test-a72243cf.md`. HEAD and `HEAD^{tree}` did not change. No tracked product file was written by this review.

## Capacity snapshot (startup)

Recorded `2026-09-26T15:58:11+00:00`. `lscpu`: 1 socket, 14 cores, 2 threads per core, 28 logical CPUs, online `0-27`. `nproc --all` = 28. `nproc` = 22. Process affinity = `0,1,8-27` (22 CPUs). Cgroup membership, effective cpuset, and CPU quota were not established: the discovery command was denied as ambiguous-sensitive-shell, and the rewritten cgroup read was circuit-broken. No affinity-widening probe was run. Conservative choice: one CPU-bound test process, no extra workers. Quota remains unknown.

## What was reviewed

The issue #58 contour on this HEAD: repository binding for a delegated `git push`, in `.grok-stack/adaptive_grok/_policy_legacy.py` (`push_repository_mismatch` and the `evaluate_pre_tool` call), the shared root-alias list consumed by `.grok/hooks/_lib.py`, and `tests/test_push_repository_binding.py`. Compared with `origin/main`, that contour is 906 lines added in `_policy_legacy.py`, the hook alias import, and 714 lines of tests, plus the change package.

Scratch, outside the worktree, mode `0700`, parent not sticky: `/home/pall/.cache/issue58-code-review-a72243cf`. `src/` is `git archive` of `a72243cf` plus the untracked `next-gap.md`. `proj/` is a copy of that snapshot with its own `git init`, one seed commit, and `origin` = `git@github.com:Dimkox/adaptive-grok-build-pro.git`. Foreign repository: `/home/pall/.cache/issue58-code-review-a72243cf/outside`. Hook probes ran `proj/.grok/hooks/pre_tool_use.py` so denial ledger writes stayed in the scratch copy.

## Finding 1 — a separate-argument global option hides the push (FAIL)

`_collect_push_invocations` only consumes `-C`, `-c`, `--git-dir`, `--work-tree`, `--config-env`, and the inline `=` forms it knows. Every other dashed global token is skipped as one flag, and the first following word that does not start with `-` ends the scan. A later `push` is recorded only when `shifted` is already set. `shifted` is set for an unreadable `-C` / `--git-dir` / `--work-tree` / `-c` value, not for an unknown option that took a separate operand.

```977:984:.grok-stack/adaptive_grok/_policy_legacy.py
            if option.startswith('-'):
                index += 1
                continue
            break
        if index >= len(bounded) or bounded[index].lower() != 'push':
            if shifted and any(token.lower() == 'push' for token in bounded[index:]):
                found.append(_unattributable_push())
            continue
```

When no push invocation is recorded and the walk is not obstructed, `push_repository_mismatch` returns `None` (`_policy_legacy.py` around 1437–1441). The legacy destructive regex still requires `git` and `push` to be adjacent (`DESTRUCTIVE_COMMANDS`, `\bgit\s+push\s+`). `_production_action` stops at the same unknown global option, so the command is not classified as `git-push-branch` and the grant check never runs. The hook's own git-root walk in `_command_directory_aliases` (`_lib.py` around 268–301) breaks on the same unknown token, so it does not record `-C` and does not mark the root ambiguous. With no sensitive action and a session root, `pre_tool_use.py` calls `evaluate_pre_tool` and allows the command.

Git 2.43.0 actually accepts the split form and still honors a later `-C`. Observed `rev-parse --show-toplevel` (no push was executed):

| Command | Exit | Toplevel |
| --- | --- | --- |
| `git --namespace foo -C <outside> rev-parse --show-toplevel` | 0 | `/home/pall/.cache/issue58-code-review-a72243cf/outside` |
| `git --attr-source HEAD -C <outside> rev-parse --show-toplevel` | 0 | same foreign toplevel |
| `git --namespace=foo -C <outside> rev-parse --show-toplevel` | 0 | same foreign toplevel (policy still sees `-C`; see controls) |
| `git --config-env protocol.version=PATH -C <outside> rev-parse --show-toplevel` | 0 | foreign toplevel, but the parser already marks `--config-env` unresolved |
| `git --exec-path /usr/lib/git-core -C <outside> rev-parse --show-toplevel` | 0 | printed `/usr/lib/git-core` and did not run rev-parse; not claimed as a push |
| `git --super-prefix foo -C <outside> rev-parse --show-toplevel` | 129 | `unknown option: --super-prefix` on this git |

Installed-hook decisions on the scratch project (snapshot of this HEAD):

| Payload | Decision | Reason |
| --- | --- | --- |
| `git -C <outside> push origin feature` | deny | `Sensitive action git-push-branch denied: root resolution status is unrecognized-command-root.` |
| `git --namespace=foo -C <outside> push origin feature` | deny | push guard: resolves in `<outside>`, grant bound to `<proj>` |
| `git --namespace foo -C <outside> push origin feature` | **allow** | empty allow |
| `git --attr-source HEAD -C <outside> push --force origin feature` | **allow** | empty allow |
| `git --namespace foo push --force origin feature` | **allow** | empty allow |

So a live hook allows a push that git will run in another repository, and it allows `--force` both there and in the bound repository. No delegated grant is required, because the command is not recognized as a production action. That breaks AC-001, AC-006's "the local repository is the bound one" premise, FORBID-001 (force / lease / `+refspec` stay unauthorized after global options), and INV-004 (a skipped group that still runs `git ... push` must be refused). The repair note at `evidence/code-review-repair-20260926.md` says force, lease, deletion, mirror, prune, and `+refspec` remain ungrantable after Git global options. That is true only for the option spellings the scanner consumes.

The 56-test module does not contain `--namespace`, `--attr-source`, or any other unknown global option with a separate operand. A green run therefore does not lock this claim.

## Finding 2 — `pushurl` in the repository config is not the destination (FAIL)

`_configured_remotes` keeps only `url =` values. `remote.<name>.pushurl` is the URL git uses for the push when it is set. Command-line `git -c remote.origin.pushurl=<foreign>` is refused (`test_command_scoped_git_configuration_cannot_redirect_origin`), but the same key already stored in `.git/config` is ignored.

Probe, scratch `proj` only:

- `git remote get-url origin` → `git@github.com:Dimkox/adaptive-grok-build-pro.git`
- `git remote get-url --push origin` → `https://example.invalid/looted.git`
- Hook payload `git push origin feature` → deny, reason `active route is missing or malformed`

That reason is `gate_block_reason` in `evaluate_pre_tool`, which runs only after `push_repository_mismatch` returns `None`. The binding guard did not reject the destination. A scratch project with no route cannot show the final allow; the suite's own allow case is plain `git push origin feature` once a route and `git-push-branch` grant exist (`test_push_to_a_remote_the_bound_repository_configures_is_allowed`). The known-limits text covers `include` / `includeIf` and `url.<base>.insteadOf`, not `pushurl` in the file this function already parses. A same-command `git config remote.origin.pushurl … && git push origin …` was not executed: shell text containing `&&` was circuit-broken before the payload could be written. That shape is unexecuted, not claimed as an observed allow.

## Controls that held

- Equals-form `--namespace=foo` does not hide a following `-C`. The push guard denies and names both repositories.
- A plain `git -C <foreign> push` is denied by the hook before the push runs (unrecognized command root). The destructive denylist still blocks adjacent `git push --force`: a shell whose text was `git push --force origin feature` was denied with `\bgit\s+push\s+[^\n]*(?:--force|-f\b)`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q tests.test_push_repository_binding` against this worktree: `Ran 56 tests in 19.780s` — `OK`. Those tests still lock the shapes they name (nested `cd` / `-C` / `--git-dir`, tool `directory`, zero-whitespace `&&`, `-c` / `GIT_CONFIG_*` / `--config-env`, destructive forms after a parsed `-C`, symlink and size caps on config reads). They do not see Finding 1.

## Mutation accounting

Scratch source: `/home/pall/.cache/issue58-code-review-a72243cf/src` (archive of `a72243cf`). Hook fixture: `.../proj`. Foreign git dir: `.../outside`. Git under test: `git version 2.43.0`.

| Claim | Probe | Result |
| --- | --- | --- |
| Split `--namespace <name>` cannot hide `-C` and `push` | git rev-parse plus scratch hook, unmutated snapshot | **survived** — git selects the foreign toplevel; hook allows |
| Split `--attr-source <tree>` cannot hide `-C`, `push`, and `--force` | same | **survived** — hook allows |
| Split `--namespace` cannot hide `--force` in the bound repo | scratch hook `git --namespace foo push --force origin feature` | **survived** — hook allows; no grant required |
| Equals-form `--namespace=<name> -C <foreign> push` stays denied | scratch hook | **killed** — push-guard deny names both paths |
| Plain `git -C <foreign> push` stays denied | scratch hook | **killed** — unrecognized-command-root |
| Adjacent `git push --force` stays denied | live shell denylist on the worktree hook | **killed** — destructive-regex deny |
| Repository `pushurl` must not count as the configured `url` | `git remote get-url` vs `get-url --push`, then hook `git push origin feature` | **survived** at the guard — mismatch is `None`; later missing-route deny. Final allow-with-grant not executed in this fixture |
| Deleting the `shifted` unattributable branch is killed by `test_unquoted_command_substitution_after_dash_c_fails_closed` | source edit in scratch | **unexecuted** — write outside the repository root was blocked, and `python3 -c` / parenthesized shell text was circuit-broken, so the mutant was not applied |
| `git config … && git push origin` rewrites the destination after the config read | hook payload | **unexecuted** — command text with `&&` was circuit-broken |
| Official `tree_fingerprint()` before/after | `adaptive_grok.util.tree_fingerprint` | **unexecuted** — `python3 -c` was circuit-broken with the earlier cgroup denial. Identity used instead: HEAD, `HEAD^{tree}`, and `git status` / `git ls-files --others --exclude-standard` |

File digests observed while the extra untracked reports were present:

- `next-gap.md` sha256 `035b90fd8a530471de417ebe35fbc506fbd35b77f2651c588f5bd8aef86b4e3c`
- `review-test-a72243cf.md` sha256 `31905eef40392d6c2523e25e2c058c6c436dcdf6bc74f78a10b01bee95bc26eb` (not part of the tree at probe start; written by the other reviewer)

## Not charged against this patch

These remain the named limits in `requirements.md` and were not treated as new defects: remote-tip ancestry, git aliases, `GIT_SSH_COMMAND` / command-running environment, an unknown wrapper executable, path-versus-origin-slug identity, shell functions, and `include` / `insteadOf`. `--exec-path <path>` was not charged: on this git it prints the exec path and does not run the following `push`.

VERDICT: FAIL

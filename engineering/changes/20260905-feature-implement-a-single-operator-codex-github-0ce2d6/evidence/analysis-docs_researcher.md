# Documentation research — Codex Linux isolation and exact GitHub proposal effects

## Scope and evidence boundary

Read-only research for route `0ce2d62a018e`, bound to control HEAD
`6f3b6ed2853b7a6f78804888cffca578d4dc9448`. I opened only official OpenAI,
GitHub CLI, GitHub REST, and Git documentation; inspected local CLI help and
binary/package metadata; and ran sandbox-only `/bin/true` and containment
probes. I did not invoke a model, read authentication/configuration files, call
GitHub, push, create a pull request, or perform any external write. The
containment probe attempted one deliberately denied host-filesystem mutation;
the path remained absent.

## Ruling

The initial host snapshot was **not ready for the live Codex call**. The
authoritative local smoke for the installed CLI returned exit `1` before
`/bin/true` ran:

```text
$ codex sandbox -P :workspace \
    -C /home/pall/grok-projects/adaptive-grok-build-pro-pilot -- /bin/true
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
sandbox_exit=1
```

After the host administrator installed the distribution AppArmor support,
installed and loaded the scoped `bwrap-userns-restrict` profile, the same exact
Codex smoke returned `0`. A single follow-up boundary probe also denied a write
outside the workspace (`EROFS`) and denied creation of an IPv4 socket (`EPERM`),
while leaving the outside sentinel absent. Therefore the specific
`RTM_NEWADDR` host prerequisite is remediated and the requested no-op plus
filesystem/network boundary checks now pass. This does **not** itself authorize
a model invocation or any GitHub effect; the remaining supervisor checks below
still apply.

Do not fall back to unsandboxed Codex. The supported fail-closed path is:

1. repair the distribution `bubblewrap`/AppArmor setup using the official
   Ubuntu 24.04 procedure;
2. require the installed Codex sandbox smoke and the product's filesystem and
   network-denial probes to pass in the exact candidate environment;
3. run one `codex exec` with `workspace-write`, approval policy `never`, command
   network disabled, no extra writable roots, an empty/allowlisted subprocess
   environment, and ephemeral state;
4. if the repaired host still cannot create the inner bwrap/seccomp sandbox,
   use an outer secure Dev Container that grants bwrap the needed capabilities
   **and keep the inner Codex sandbox enabled**;
5. if only `danger-full-access` works inside the container, keep the live pilot
   blocked. OpenAI documents that mode as an outer-container fallback but also
   warns that malicious project content can exfiltrate everything available in
   that container, including Codex credentials. That does not meet this pilot's
   untrusted-issue/no-tool-network boundary.

## Official OpenAI findings

- [Sandbox](https://learn.chatgpt.com/docs/sandboxing) says Linux/WSL2 requires
  `bubblewrap`, Codex uses the first `bwrap` on `PATH`, and Ubuntu 24.04 may need
  the `bwrap-userns-restrict` AppArmor profile installed and loaded. It prefers
  that scoped profile over globally disabling the unprivileged-user-namespace
  restriction.
- [Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security)
  states that Linux uses `bwrap` plus seccomp by default; spawned commands
  inherit the sandbox; `workspace-write` has command network off by default;
  and the client's model/authentication requests are separate from command
  network policy. This is the required separation: Codex can reach its provider
  while model-generated commands remain offline.
- The same page documents an outer Dev Container when namespaces/setuid bwrap
  or seccomp are blocked, and explicitly warns about credential exfiltration
  when Codex is run with `danger-full-access` inside it. Its secure example uses
  an allowlist firewall and can retain the inner bwrap sandbox when the container
  grants the needed capability.
- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
  documents `codex exec --sandbox workspace-write`, `--ephemeral`, `--json`,
  `--output-schema`, `--ignore-user-config`, and `--ignore-rules`; it calls
  `--full-auto` deprecated. It also says to expose `CODEX_API_KEY` only to the
  Codex invocation and never to untrusted code in the same process environment.
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
  documents `sandbox_workspace_write.network_access`, writable-root and `/tmp`
  exclusions, `shell_environment_policy.inherit`, canonical environment filters,
  `web_search`, and strict permission/sandbox settings. Local `network_proxy` is
  experimental and is not needed when command network is disabled; an allowlist
  proxy is not equivalent to this pilot's zero tool egress.

### Initial failing host snapshot

```text
OS: Ubuntu 24.04.4 LTS; kernel 6.8.0-110-generic x86_64
kernel.unprivileged_userns_clone: 1
kernel.apparmor_restrict_unprivileged_userns: 1
bubblewrap package: 0.9.0-1ubuntu0.1; /usr/bin/bwrap mode 0755
/etc/apparmor.d/bwrap-userns-restrict: missing
/usr/share/apparmor/extra-profiles/bwrap-userns-restrict: missing
apparmor-profiles: not installed
apparmor-utils: not installed
```

Installed Codex identity:

```text
codex-cli 0.153.4
/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex
sha256 56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da
```

The `RTM_NEWADDR` message means bwrap failed while setting an address on the
new namespace's loopback device. At that snapshot, the missing Ubuntu 24.04
AppArmor profile was the first officially supported remediation, but the data
did not prove AppArmor was the sole root cause. Package presence or a one-off
raw `bwrap` result alone is not readiness evidence; the actual Codex sandbox
probe plus explicit containment tests remain the gate.

### Administrator remediation and post-remediation observation

The official Ubuntu 24.04 sequence is:

```bash
sudo apt update
sudo apt install bubblewrap apparmor-profiles apparmor-utils
sudo install -m 0644 \
  /usr/share/apparmor/extra-profiles/bwrap-userns-restrict \
  /etc/apparmor.d/bwrap-userns-restrict
sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict
```

The host administrator subsequently performed that scoped remediation. The
docs researcher did not execute the privileged changes. Current read-only host
inspection found:

```text
apparmor-profiles=4.0.1really4.0.1-0ubuntu0.24.04.7
apparmor-utils=4.0.1really4.0.1-0ubuntu0.24.04.7
bubblewrap=0.9.0-1ubuntu0.1
/etc/apparmor.d/bwrap-userns-restrict mode=644 owner=root:root
```

The administrator separately observed the profile load and an independent
raw-bwrap network-namespace smoke printing `sandbox-ok`. More importantly, the
installed Codex CLI itself now crosses the previously failing setup boundary:

```text
$ codex sandbox -P :workspace \
    -C /home/pall/grok-projects/adaptive-grok-build-pro-pilot -- /bin/true
codex_sandbox_noop_exit=0
```

One no-model containment probe then attempted `os.open(..., O_CREAT|O_EXCL)` on
the exact outside sentinel `/home/pall/.codex-sandbox-smoke-0ce2d62a` and an
IPv4 UDP socket directed at the documentation-only address `192.0.2.1:9`. No
datagram payload was sent: the kernel denied `socket(AF_INET, SOCK_DGRAM)`
itself. Captured output was:

```text
fs_denied_errno=30
PermissionError: [Errno 1] Operation not permitted
combined_probe_exit=1
outside_path_absent_exit=0
```

This is a boundary **pass**, not an isolation failure: errno `30` is `EROFS`
for the outside write, errno `1` is `EPERM` at socket construction, and the
sentinel remained absent. The probe harness returned `1` only because it had
expected to catch a later `connect()` denial and did not catch the stronger,
earlier constructor denial. It was not repeated.

Do not use the documented global
`kernel.apparmor_restrict_unprivileged_userns=0` escape for this pilot: it
widens the host boundary and is unnecessary if the scoped profile/container
path works. Any administrator change needs its own authorization and evidence.

### Version-specific CLI behavior

Local `codex exec --help` confirms `--sandbox`, `--strict-config`,
`--ignore-user-config`, `--ignore-rules`, `-C`, `--ephemeral`, `--json`, and
`--output-schema`. The approval flag is global in this build, so `-a never`
must precede `exec`.

The current `codex sandbox --help` uses platform-implicit syntax:

```text
Usage: codex sandbox [OPTIONS] [COMMAND]...
```

It does **not** expose the documentation's `sandbox linux` subcommand. On this
0.153.4 build, `codex sandbox linux --help` treated `linux --help` as the sandboxed
command and failed during bwrap setup. Use the locally advertised form for the
preflight:

```bash
"$PINNED_CODEX" sandbox -P :workspace -C "$CANDIDATE_ROOT" -- /bin/true
```

After the no-op passes, the supervisor must also prove, under the same profile,
that: a write inside the candidate succeeds; a write to a private sentinel
outside it fails without mutation; direct TCP/UDP and Unix-socket access fail;
and `.git`/publisher/provider credential locations are absent or protected.
The requested outside-filesystem and IPv4-network denial sample now passes as
recorded above; it does not replace the other product preflights. Any unexplained
nonzero, timeout, unexpected output, or unverifiable sentinel is terminal
`sandbox_unavailable`; do not retry the Codex attempt. A known harness nonzero
caused by a stronger-than-expected denial may be classified only from captured
evidence, as done above, never silently ignored.

### One-call invocation skeleton (after preflight only)

Construct this as an argv/environment array, not a shell string. Paths, model,
schema, binary digest, and limits come only from the trusted repository profile.

```bash
env -i \
  PATH=/usr/bin:/bin \
  HOME="$PRIVATE_HOME" \
  CODEX_HOME="$PRIVATE_CODEX_HOME" \
  "CODEX_API_KEY=${ONE_RUN_CODEX_TOKEN}" \
  LC_ALL=C.UTF-8 TZ=UTC \
  "$PINNED_CODEX" -a never exec \
    --strict-config \
    --ignore-user-config \
    --ignore-rules \
    --ephemeral \
    --sandbox workspace-write \
    -C "$CANDIDATE_ROOT" \
    --model "$PINNED_MODEL" \
    -c 'sandbox_workspace_write.network_access=false' \
    -c 'sandbox_workspace_write.exclude_slash_tmp=true' \
    -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true' \
    -c 'web_search="disabled"' \
    -c 'shell_environment_policy.inherit="none"' \
    -c 'shell_environment_policy.ignore_default_excludes=false' \
    --json \
    --output-schema "$READ_ONLY_OUTPUT_SCHEMA" \
    -
```

The supervisor must provide only a minimal trusted subprocess environment (add
fixed `PATH`, locale, timezone, and sterile Git variables through the explicit
policy if the selected tools require them), bound stdout/stderr/time/process
group, and count the process start durably before `exec`. The private
`CODEX_HOME` must contain no durable user configuration, MCP/app/plugin setup,
or reusable authentication. Reject a target containing effective repo-local
Codex hooks/configuration unless it is explicitly represented in the sealed
profile. Never add writable roots, enable web search, enable command network,
resume, fork, or make a second call.

## Official GitHub/Git findings

- [Git push documentation](https://git-scm.com/docs/git-push) permits a full
  object ID as `<src>` and a fully qualified destination ref; a leading `+` or
  `--force` overrides the normal fast-forward rule. `--porcelain` emits
  machine-readable full refs and distinguishes new (`*`), up-to-date (`=`),
  forced (`+`), and rejected (`!`) outcomes.
- [GitHub push documentation](https://docs.github.com/en/get-started/using-git/pushing-commits-to-a-remote-repository)
  confirms ordinary pushes reject non-fast-forward updates and supports an
  explicit local-to-remote branch mapping.
- [`gh pr create`](https://cli.github.com/manual/gh_pr_create) says explicit
  `--head` skips its implicit push/fork behavior, `--body-file` avoids inline
  body interpolation, and `--no-maintainer-edit` disables the offered head-edit
  capability. Its `--dry-run` **may still push**; it is not safe preflight.
  `--recover` restores failed interactive input and is not an idempotency key.
- [`gh pr list`](https://cli.github.com/manual/gh_pr_list) can filter by head,
  base, and all states and return `headRefOid`, `baseRefOid`, IDs, state, body,
  and repository fields as JSON. Its `--head` filter does not accept
  `<owner>:<branch>`; this pilot's same-repository head uses the bare branch.
- [`gh pr view`](https://cli.github.com/manual/gh_pr_view) exposes the same exact
  head/base OIDs and PR identity for post-create verification.
- [`gh help environment`](https://cli.github.com/manual/gh_help_environment)
  documents `GH_PROMPT_DISABLED`, process-scoped `GH_TOKEN`, explicit `GH_REPO`,
  update-notifier controls, and telemetry controls.
- [GitHub REST Git references](https://docs.github.com/en/rest/git/refs) provides
  exact ref observation and create/update semantics. Ref creation returns `201`;
  conflict/validation is `409`/`422`; update defaults to `force=false`.
- [GitHub REST pull requests](https://docs.github.com/en/rest/pulls/pulls) makes
  create a `201` effect and list filterable by `head=user:ref` and `base`; a
  `422` is ambiguous between validation and abuse/rate limiting and must not be
  interpreted as proof that no PR exists.

Local GitHub CLI is `gh 2.86.0-112-gc30647b78`; local Git is `2.43.0`. Their
help matches the cited `--head`, `--base`, `--body-file`,
`--no-maintainer-edit`, filter, and JSON-field behavior.

### Exact non-force branch upload

Use a publication-only copy of the sealed repository, a collision-resistant
branch name committed before the effect, an explicit trusted remote, sterile
Git configuration, one full-SHA/full-ref refspec, and no `+`, force, tags,
upstream, mirror, or implicit refspec:

```bash
git -C "$SEALED_REPOSITORY" \
  -c core.hooksPath=/dev/null \
  -c push.default=nothing \
  -c push.followTags=false \
  -c remote.origin.mirror=false \
  push --porcelain --no-force --no-follow-tags \
  "$AUTHENTICATED_EXACT_REMOTE" \
  "$CANDIDATE_SHA:refs/heads/$PROPOSAL_BRANCH"
```

The credential comes from the publisher's private process environment/helper;
it must not be embedded in the URL, repository config, argv evidence, or model
workspace. Before the grant/effect, observe that the exact destination ref is
absent and the base ref still equals the bound base SHA. Accept only porcelain
`*` for the intended full ref, then independently read the remote ref and require
`object.sha == CANDIDATE_SHA`. On timeout/ambiguous output, do not push again;
perform read-only exact-ref reconciliation. Exact match may be adopted, missing
or differing ref is terminal ambiguity.

Important residual: ordinary non-force Git permits a fast-forward update if a
different actor creates that ref between the absence check and push. It has no
create-only compare-and-swap flag that is both atomic and free of force
semantics. `--force-with-lease=<ref>:` would express expected absence but is a
force-class operation and is outside this requirement. Therefore require a
high-entropy run/candidate-bound branch plus pre/post observation, or a
receive-side/create-ref design approved by the architecture/security owner;
otherwise the strict “one newly created ref” invariant remains blocked.

### Exact PR creation and reconciliation

Invoke `gh` as argv with a process-scoped least-privilege token, explicit repo,
base, already-pushed head, trusted title, and private mode-`0600` body file:

```bash
env GH_PROMPT_DISABLED=1 GH_NO_UPDATE_NOTIFIER=1 GH_TELEMETRY=0 \
  "GH_TOKEN=${ONE_EFFECT_GITHUB_TOKEN}" \
  gh pr create \
    --repo "$OWNER/$REPO" \
    --base "$BASE_BRANCH" \
    --head "$PROPOSAL_BRANCH" \
    --title "$TRUSTED_TITLE" \
    --body-file "$PRIVATE_BODY_FILE" \
    --no-maintainer-edit
```

The body should include a stable candidate/run digest marker and should never be
interpolated into a shell. `--head` is mandatory so `gh pr create` cannot decide
to push or fork. Never use `--dry-run`, `--fill`, `--web`, or `--recover` in the
actuator.

On any timeout/nonzero/malformed response, do not create again. Reconcile only:

```bash
env GH_PROMPT_DISABLED=1 GH_NO_UPDATE_NOTIFIER=1 GH_TELEMETRY=0 \
  GH_TOKEN="$READ_TOKEN" \
  gh pr list \
    --repo "$OWNER/$REPO" \
    --state all \
    --base "$BASE_BRANCH" \
    --head "$PROPOSAL_BRANCH" \
    --limit 100 \
    --json id,number,url,state,isDraft,body,headRefName,headRefOid,headRepository,headRepositoryOwner,baseRefName,baseRefOid,maintainerCanModify
```

Adopt only exactly one PR whose repository, head ref/OID, base ref/OID at the
effect boundary, candidate marker, draft policy, and maintainer-edit policy all
match the sealed proposal. Confirm it by number using `gh pr view --repo ...
--json ...`. Zero, multiple, or mismatched results are
`external_outcome_ambiguous`; do not retry, edit, close, or merge.

## Required go/no-go checks before a live pilot

1. Pinned Codex binary/version/digest matches the stored profile.
2. Actual Codex sandbox and denial probes pass once in the exact runtime; the
   current no-op and requested outside-filesystem/IPv4-denial samples pass, and
   any remaining probe failure stops before counting a model attempt.
3. Codex process gets provider auth only; tool subprocess environment and
   filesystem cannot reach it; command network/web/MCP/apps are unavailable.
4. Publisher process and credential are created only after the sealed candidate,
   targeted test, semantic pass, and exact grants; they never enter Codex.
5. Remote base/ref observations and every effect/response are digest-bound and
   committed durably. Ambiguity permits observation, not an automatic effect
   retry.
6. Branch and PR commands are separately granted. Nothing here authorizes
   merge, close, comment, label, deployment, release, or Trust CI mutation.

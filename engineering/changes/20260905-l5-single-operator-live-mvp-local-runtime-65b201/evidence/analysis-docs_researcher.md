# Primary-doc constraints for the smallest live design-partner pilot

## Evidence binding and scope

- Route: `65b2018b786d`.
- Source inspected: Git HEAD `f3f8d7375a153393ffba3906165e8d625e45d4a1`, tree `a8f8d71a745e69b12f630d73ba11e1cdca262c5e`.
- Research date: 2026-09-05 UTC.
- This is read-only analysis. No Codex model invocation, GitHub/cPanel mutation, credential read, push, PR, check run, deployment, or other external write was performed.
- Sources are current primary OpenAI and GitHub documentation plus locally inspected repository/CLI facts. Statements below are marked **Verified** or **Inference / pilot constraint** so documentation claims are not confused with design decisions.

## Codex CLI: verified behavior and bounded use

**Verified — official OpenAI documentation.** `codex exec` is the supported non-interactive entrypoint. Its final message goes to stdout and progress goes to stderr by default; `--json` changes stdout to a JSONL event stream; `--output-schema` constrains the final response to a supplied JSON Schema; `--output-last-message` writes only the final message to a file. `--ephemeral` avoids persisting session rollout files. The default `exec` sandbox is read-only, while `workspace-write` and `danger-full-access` are explicit alternatives. See [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) and the [Codex CLI command reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

**Verified — local executable.** The inspected host resolves `codex` to `/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex`: `codex-cli 0.153.4`, SHA-256 `56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da`, mode `0755`, owner `1000:1000`, size `258659424`. Local `codex exec --help` advertises `--image`, `--sandbox`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--output-schema`, `--json`, `--output-last-message`, `--cd`, `--add-dir`, and stdin prompt `-`; top-level help advertises `--ask-for-approval never`. The local binary, not a potentially newer documentation page, is the execution contract for this checkpoint.

**Verified — image input.** The CLI accepts one or more images using repeated or comma-separated `--image`; OpenAI documents common formats including PNG and JPEG and recommends telling the model what to inspect. See [Image inputs](https://learn.chatgpt.com/docs/image-inputs).

**Verified limitation.** The inspected official CLI reference exposes image attachment but no native PDF or DOCX attachment flag. It also does not publish a CLI-specific maximum image count, image/file byte limit, prompt/output byte limit, cost ceiling, or deterministic latency bound. `--output-schema` constrains response shape; it is not a guarantee that untrusted content is safe. `--sandbox read-only` restricts filesystem command effects but the cited docs do not claim that it disables all tools or all outbound capability. The local help exposes no `--no-tools` switch.

**Inference / mandatory pilot constraints.** The smallest defensible runner should therefore:

1. Pin and re-check the exact executable path, version, and digest above; fail closed on drift. Pin one exact model ID and prohibit fallback.
2. Use one fresh process per job, no `resume`, no automatic model retry, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--strict-config`, `--ask-for-approval never`, `--sandbox read-only`, a sterile read-only working directory, `--output-schema`, `--json`, and prompt stdin. Never place partner content in argv.
3. Parse JSONL by event type and require exactly one successful terminal result whose final payload validates against the closed schema. Bound wall time, process count, stdin bytes, stdout/stderr bytes, event count, and attempts locally; kill the process group on any ceiling.
4. Treat PDF and DOCX as untrusted inputs to deterministic, locally pinned extraction and normalization before Codex. Do not describe them as native Codex attachments. Reject encrypted, malformed, over-limit, macro/embedded-object, or extraction-ambiguous files into `needs_human`.
5. Validate image MIME from bytes, dimensions, decoded pixel count, and bytes before passing an image path/file descriptor. A focused local activation test must prove that the selected path/file-descriptor mechanism works with this exact CLI; documentation does not prove inherited-FD behavior.
6. Treat all model output as a non-authoritative draft. Trusted application code derives job IDs, repository coordinates, filenames, hashes, policy identity, and allowed transitions.
7. Keep `CODEX_API_KEY`/saved authentication outside job input, output, logs, database payloads, and child environments except the exact Codex process. OpenAI describes `auth.json` as password-equivalent and recommends scoping `CODEX_API_KEY` only to the Codex process in automation; see [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

A suitable argv shape, subject to the exact local activation test, is:

```text
<pinned-codex> --ask-for-approval never exec --strict-config \
  --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check \
  --sandbox read-only --cd <sterile-read-only-dir> --model <exact-model-id> \
  --output-schema <read-only-schema> --json [--image <validated-image>] -
```

The current official docs call `--full-auto` deprecated; the local `0.153.4` `exec` help does not advertise it. Do not depend on that shortcut.

## GitHub: exact-SHA delivery and acceptance

### Verified mechanics

| Operation | Official fact | Pilot constraint |
|---|---|---|
| Issue intake | Creating an issue is `POST /repos/{owner}/{repo}/issues` and needs Issues write permission; automated creation can trigger notifications and secondary rate limits. [Create an issue](https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#create-an-issue) | Prefer a human-created design-partner issue for the first pilot. Snapshot issue number, `updated_at`/ETag when available, and a body digest before execution; later edits are new input, not silent mutation. |
| Branch | A branch is a fully qualified Git ref such as `refs/heads/...` pointing to a required commit SHA. Creating it uses Contents write permission. Updating a ref supports `force`, default `false`. [Git references](https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#create-a-reference) | Create a unique feature ref from the recorded base SHA, never force-update it, then read it back and require its remote SHA to equal the locally verified commit SHA. Branch names are mutable labels; SHA is identity. |
| Pull request | Creating a PR requires existing `head` and `base` refs and Pull requests write permission; draft PRs are supported. [Create a pull request](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request) | Open a draft PR only after remote ref reconciliation. Persist PR number, base SHA, and observed head SHA. A later head/base change invalidates the previous acceptance tuple. |
| Check run | A check run is created for an explicit `head_sha`; GitHub states check-run creation is a GitHub App operation and requires Checks write permission. [Create a check run](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run) [Checks guide](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks) | Only the deployed Trust CI GitHub App may publish the repository's required policy-epoch check. A same-named status, local receipt, model result, issue label, or delivery-App check is not equivalent. |
| Protection | Required checks can be bound to an expected GitHub App; strict checks require the PR branch to be current with the base branch. Required checks must succeed on the latest commit SHA. [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) [Troubleshooting required checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks) | Gate the exact latest PR head, not a previous commit. A base refresh or new commit requires a fresh exact-head check and renewed human review under the repository policy. |
| Human review | A PR review can record `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`. [Create a review](https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#create-a-review-for-a-pull-request) | The single operator reviews the latest diff and generated artifacts using a human identity. The automation must not self-approve or simulate acceptance. |
| Merge guard | GitHub's merge endpoint accepts an expected PR head `sha` and returns conflict when it does not match. [Merge a pull request](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#merge-a-pull-request) | A future separately authorized merge must supply the accepted exact SHA and reject mismatch. This route authorizes no merge. |

**Verified — repository-local contract, not a live GitHub re-check.** `PROJECT_STATE.json`, `START_HERE.md`, and `README.md` identify the current required context as `adaptive-trust-ci/verified@06ecf1c875bc`, policy digest `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`, bound GitHub App ID `4694114`. The suffix is a policy epoch and may change; consumers must read the currently deployed/declared value rather than hard-code it forever. Repository history also contains the superseded `@6737355947c2`, which must not be mistaken for the current epoch.

**Verified — least privilege.** GitHub Apps begin without permissions, and installation access tokens can be reduced to selected repositories/permissions, cannot exceed the installation grant, and expire after one hour. See [Choosing GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app) and [Generating an installation access token](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

**Inference / pilot control.** Do not enlarge or reuse the Trust CI App for delivery writes. If later authorized, use a separate least-privilege delivery installation with only the scopes actually needed: Issues write only if it must create/update issues, Contents write for refs/content, and Pull requests write for PRs. Keep Checks write and the expected App identity exclusive to Trust CI. Keep App private keys and installation tokens outside source, SQLite, artifacts, and logs.

### Smallest stage sequence

1. **Local stage (authorized now):** snapshot one human-selected issue and exact base SHA; run one bounded Codex normalization; validate the closed output; build and locally verify a commit in an isolated clone; persist head SHA, tree, diff digest, artifact digests, executable/model/schema/profile digests, and the issue snapshot identity.
2. **Delivery stage (future exact external grant):** reconcile before every POST; create the non-protected branch once, confirm its exact SHA, create one draft PR, and bind its number/base/head to the job. If an ambiguous prior result exists, stop at `needs_human` rather than duplicate.
3. **Trust stage (independent):** Trust CI evaluates the latest exact head and publishes the current App-owned policy-epoch check. The delivery worker cannot create, copy, or infer success.
4. **Acceptance stage (human):** the operator reviews the latest exact-head diff/artifacts and records acceptance. Any new commit or base movement makes the stored acceptance stale.
5. **Merge/deploy stages (future, separately authorized):** merge only with the accepted expected SHA and branch protection satisfied. Deployment starts only from the immutable accepted/merged artifact identity.

For retry safety, keep a durable operation record and reconcile GitHub state before retrying: issue marker/snapshot, fully qualified ref plus exact SHA, existing PR for the same head/base, and check run by exact SHA/name/App/external ID. GitHub endpoint availability is not an idempotency guarantee.

## cPanel is downstream publishing, never the stage gate

**Verified — official cPanel documentation.** cPanel API tokens authenticate UAPI over HTTPS, and file upload uses `Fileman::upload_files` with multipart data and a destination directory. See [How to use cPanel API tokens](https://docs.cpanel.net/knowledge-base/security/how-to-use-cpanel-api-tokens/) and the [UAPI file-upload tutorial](https://api.docs.cpanel.net/guides/quickstart-development-guide/tutorial-use-uapis-fileman-upload-files-function-in-custom-code).

**Verified limitation.** Those pages document transport/authentication and upload; they do not establish atomic multi-file activation, application health, rollback, or GitHub acceptance.

**Inference / mandatory boundary.** cPanel must remain a transport-injected, disabled-by-default adapter until an exact deployment grant exists. Never upload in place as the first step. A later deployment should upload a hash-verified artifact to a unique versioned staging directory, verify remote bytes, snapshot the prior active identity, activate separately, run bounded health checks, and restore/forward-recover on failure. TLS verification is mandatory; tokens remain outside source/logs. cPanel success cannot satisfy the PR check, replace human review, or authorize merge. No cPanel activity is part of the current local stage.

## Go/no-go summary

The smallest live design-partner pilot is viable only as a chain of immutable identities: `issue snapshot + base SHA -> bounded local Codex result -> commit/tree/artifact digests -> draft PR exact head -> App-owned exact-head Trust CI check -> human acceptance of that same head -> separately authorized merge/deploy`. Unknown CLI resource limits require local ceilings; PDF/DOCX require local extraction; sandbox mode is not evidence of a complete no-tools guarantee; and every external transition remains disabled until its own exact authorization and reconciliation step.

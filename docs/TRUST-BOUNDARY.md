# Trust boundary operations

The repository files define the checks, but GitHub repository settings make them authoritative. Until the settings below are enabled, the workflows are useful evidence rather than an enforceable merge or release boundary.

## Main branch rules

Create a branch ruleset for `main` with these settings:

1. Require a pull request before merging.
2. Require at least one approval.
3. Require review from Code Owners.
4. Dismiss stale approvals when new commits are pushed.
5. Require approval of the most recent reviewable push.
6. Require all conversations to be resolved.
7. Block force pushes and branch deletion.
8. Do not allow bypass for repository writers or automation identities.
9. Require the three checks produced by `.github/workflows/trusted-ci.yml`:
   - `trusted-ci / verify-py3.10`
   - `trusted-ci / verify-py3.12`
   - `trusted-ci / package`

GitHub can display only the job suffix in some settings screens. Select both Python matrix jobs and the package job from the `trusted-ci` workflow.

## Production Environment

Create an Environment named exactly `production`:

1. Add `@Dimkox` as a required reviewer.
2. Disable self-review when that option is available.
3. Restrict deployment branches and tags to `main`.
4. Do not add agent, bot, or runner identities as reviewers.

`.github/workflows/release.yml` targets this Environment. The release job cannot start until the Environment approval is granted.

## Normal delivery

```text
feature branch
→ pull request
→ exact-SHA trusted CI
→ CODEOWNER approval
→ protected merge into main
```

Agents do not push, merge, dispatch workflows, create tags, or publish releases. `scripts/grok_approve.py` records a request only; it does not authorize any action.

## Release

After the pull request is merged and `VERSION` contains a version whose tag does not yet exist, a human runs outside the Grok tool sandbox:

```bash
gh workflow run release.yml --ref main -f version="$(tr -d '\r\n' < VERSION)"
```

Then the required reviewer approves the `production` Environment deployment in GitHub. The workflow:

1. checks out the exact `main` SHA;
2. rejects a version mismatch or existing tag;
3. runs strict release verification;
4. builds the deterministic ZIP and checksum;
5. creates an annotated tag at the verified SHA;
6. publishes the GitHub Release.

## Local commands

Local verification is useful before opening a pull request:

```bash
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_verify.py --mode pr --strict --json
python3 scripts/package_stack.py
```

Local output is not a substitute for the required GitHub checks. A local approval request, runtime receipt, or disabled hook never satisfies branch or Environment protection.

## Recovery

If trusted CI fails, repair the branch and push another commit; stale approvals must be dismissed automatically by the branch ruleset.

If release verification fails, do not create the tag manually. Repair through another pull request and dispatch the release workflow again from the new merged SHA.

If the workflow created a tag but release publication failed, inspect the run before retrying. Delete the tag only through a human-owned recovery action after confirming that no release or downstream consumer depends on it.

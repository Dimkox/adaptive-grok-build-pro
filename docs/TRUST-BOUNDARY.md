# Trust boundary operations

The repository files define the checks, but GitHub repository settings make them authoritative. Until the settings below are enabled, the workflows are useful evidence rather than an enforceable merge or release boundary.

## Install this contour into another repository

The local stack installs without GitHub workflows by default:

```bash
python3 scripts/install_into.py /path/to/repo
```

Trusted CI and protected release files are opt-in. Name the actual human owner or organization team for the target repository:

```bash
python3 scripts/install_into.py /path/to/repo \
  --with-ci \
  --codeowner @user

# organization team:
# --codeowner @org/team
```

`--with-ci` without `--codeowner` fails before writing files. The installer renders the supplied identity into `.github/CODEOWNERS` and this runbook, and conflict detection uses that rendered content. It never assigns `@Dimkox` as owner of an unrelated consumer repository.

## Choose the identity model first

GitHub pull-request authors cannot approve their own pull requests. GitHub Environment self-review prevention likewise blocks the user who initiated a deployment from approving that deployment. A personal repository therefore needs an explicit identity model instead of blindly enabling every separation-of-duties switch.

### Solo owner mode — workable now

Use this mode while pull requests and release workflow dispatches are performed as `@Dimkox`:

- require a pull request and all trusted CI checks, but set required approving reviews to **0**;
- keep `CODEOWNERS` as the human-ownership map, but do not enable **Require review from Code Owners** for pull requests authored by `@Dimkox`;
- merge only through the GitHub UI after the owner has inspected the final exact-SHA diff and all required checks are green;
- configure `@Dimkox` as the required `production` reviewer, but leave **Prevent self-review** disabled when `@Dimkox` manually dispatches the release workflow;
- disable administrator bypass of branch and Environment protection wherever GitHub exposes that option.

This is a one-human, two-step gate. It prevents the Grok agent from merging or publishing, but it is not four-eyes approval.

### Split identity mode — stronger target

Use this mode after a dedicated GitHub App, bot account, or second maintainer is available:

- the separate identity authors pull requests;
- require at least one approval and enable **Require review from Code Owners**;
- dismiss stale approvals and require approval of the most recent reviewable push;
- the separate identity or automation dispatches release workflows;
- keep `@Dimkox` as the required `production` reviewer and enable **Prevent self-review**;
- never assign the implementation agent or release runner as an approving reviewer.

This is the recommended long-term configuration because authorship, verification, approval, merge, and release authorization are separated.

## Main branch rules common to both modes

Create a branch ruleset for `main` with these settings:

1. Require a pull request before merging.
2. Require all conversations to be resolved.
3. Block force pushes and branch deletion.
4. Do not allow bypass for repository writers, administrators, or automation identities.
5. Require the three checks produced by `.github/workflows/trusted-ci.yml`:
   - `trusted-ci / verify-py3.10`
   - `trusted-ci / verify-py3.12`
   - `trusted-ci / package`
6. Select the approval settings from the chosen identity mode above.

GitHub can display only the job suffix in some settings screens. Select both Python matrix jobs and the package job from the `trusted-ci` workflow.

## Production Environment common settings

Create an Environment named exactly `production`:

1. Add `@Dimkox` as a required reviewer.
2. Restrict deployment branches and tags to `main`.
3. Disable administrator bypass of deployment protection.
4. Configure **Prevent self-review** according to the chosen identity mode.
5. Do not add the implementation agent, release runner, or other automation identity as a reviewer.

`.github/workflows/release.yml` targets this Environment. The release publication job cannot start until the Environment approval is granted.

## Normal delivery

Solo owner mode:

```text
feature branch
→ pull request
→ exact-SHA trusted CI
→ final owner inspection
→ manual owner merge into protected main
```

Split identity mode:

```text
bot or collaborator feature branch
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

In solo owner mode, the owner then approves the `production` deployment with self-review prevention disabled. In split identity mode, a separate identity dispatches the run and the owner approves it with self-review prevention enabled.

The workflow:

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

If trusted CI fails, repair the branch and push another commit. In split identity mode, stale approvals must be dismissed automatically by the branch ruleset.

If release verification fails, do not create the tag manually. Repair through another pull request and dispatch the release workflow again from the new merged SHA.

If the workflow created a tag but release publication failed, inspect the run before retrying. Delete the tag only through a human-owned recovery action after confirming that no release or downstream consumer depends on it.

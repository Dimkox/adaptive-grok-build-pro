# M2 Trust CI read-only workspace compatibility

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
Created: 2026-08-29T06:13:28+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

Исправить регрессию PR M2: корневые unittest должны проходить в изолированном Trust CI при read-only исходниках и несовпадающем владельце Git; устранить мутацию исходного дерева упаковщиком и сохранить контроль целостности без изменения deployed Trust CI policy

## Outcome

M2 architecture and packaging tests can execute in the pinned non-root Trust CI runner with `/workspace:ro` and `.git:ro`, while the repository remains unchanged. Git trust is exact and process-local, and package metadata is rendered without writing the source tree.

## Scope

### In scope

- Command-scoped `safe.directory` for every architecture Git command that operates on the exact canonical repository root.
- Pure manifest rendering and archive construction that does not create, replace, or remove the source manifest.
- A process-scoped exact-path Git config for the receipt test's required `git clone --no-local` setup.
- Symlink/non-regular exclusion, descriptor-relative no-follow source reads, identity/digest stability, and atomic archive publication on a stable snapshot.
- Bounded streaming for source hashing, ZIP members, and the completed archive checksum.
- Exclusive no-follow temporary creation whose held descriptor is written directly, identity-checked before publication, and mode-compatible with new or existing outputs.
- An explicit repository architecture limit adjustment from 10,000 to 10,820 changed lines for the measured 10,739-line compatibility diff.
- Focused regressions and documentation for the read-only compatibility boundary.

### Out of scope

- Changes under `trust-ci/**`, deployed Trust CI policy or holdout, runner images, runtime services, signing material, or external systems.
- Making the checkout, `.git`, or package source writable; changing ownership; wildcard Git trust; persistent Git configuration.
- Following repository symlinks or accepting source identity/content drift between manifest hashing and archive streaming.
- Reopening the temporary archive by pathname, following a swapped temporary name, or changing normal output permission semantics.
- Public API, event, or data contract changes.
- Full verification, independent reviews, receipts, transition to `ready`, push, merge, release, or deployment in this implementation step.

## Constraints

- Backward compatibility: `generate_manifest(root)` remains an explicit source-writing API; archive name, layout, ordering, modes, exclusions, and checksum sidecar stay stable.
- Data/privacy: no secrets or host Git configuration are read; the receipt fixture's temporary Git config contains only the exact public repository Git path.
- Performance: packaging enumerates included paths once, streams each file once for its manifest hash and once into the archive, then streams the completed ZIP checksum; only paths, metadata, bounded chunks, and synthetic manifest bytes are retained in memory.
- Operational: the repair must work with UID/GID `10001:10001`, `/workspace:ro`, and `.git:ro`, and must not relax source-mutation detection.
- Architecture: the changed-line ceiling remains finite and requires architecture, governance, and security approval scopes.

## Reproduction evidence

The pinned runner reproduced five architecture Git failures because `architecture_diff._git_environment` replaced the outer `safe.directory`; the receipt fixture's `git clone --no-local` failed when child `upload-pack` rejected `/workspace/.git` ownership; and packaging failed while attempting to write root `MANIFEST.sha256`. After those repairs, the secondary pinned RED measured 10,043 changed lines against the repository's exact 10,000-line ceiling; security remediation raised the final governed measurement to 10,739, which the explicit 10,820 limit admits with 81 lines of headroom.

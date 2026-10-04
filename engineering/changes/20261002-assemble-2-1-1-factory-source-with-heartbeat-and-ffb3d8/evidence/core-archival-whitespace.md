# Exact approved-design archival whitespace control

Controller authorized only the existing exact-path `.gitattributes` `whitespace=-trailing-space` precedent for `engineering/changes/20261002-assemble-2-1-1-factory-source-with-heartbeat-and-ffb3d8/approved-recovery-design.md`. Lines3-6 end in two spaces, the Markdown hard-break syntax; trimming them changes the approved original bytes. Source SHA256 remains `1d6ef0470458ac5f061fec8af2d6da26545389739fee98f395d5d5b7b7759f6b` before and after the exact-path attribute.

Before the attribute, `git diff --cached --check` returned2 and reported only those four archival lines. Afterward, the unchanged normal `git diff --cached --check` returned0. No wildcard/global Git configuration, code budgets, verification selectors, runtime, security or external Trust CI policy changed.

Writer preparation control, not independent review: private scratch `<local-path>` observed mode0700, owned by pall under project runtime. `git init -q`, `git add -- .gitattributes ordinary-control.md engineering/changes/20261002-assemble-2-1-1-factory-source-with-heartbeat-and-ffb3d8/approved-recovery-design.md`, `git diff --cached --check`:exit2, exact concise output `ordinary-control.md:1: trailing whitespace.` and no approved-design finding. The scratch design SHA256 equals the approved original. Scratch activity did not alter the candidate product; runtime records remain ignored.

Independent code/test reviewers must repeat this negative control in their own safe private snapshots. That independent claim is UNEXECUTED here; the writer does not approve its own change. Keep all Git whitespace checks enabled on final base..HEAD/staged/unstaged inventories.

# Next external pilot preparation

The September 21 continuation identified a concrete successor task: the landing's
browser audit omits `/ru/` and `/ru/roadmap.html` on target commit
`6226aa0b86e1fe08c63724cc3761b3f788146b91`. This folder is a read-only investigation
and an unposted issue draft, not an implementation, approved target policy, provider
attempt or accepted pilot outcome. Issue #155 remains the active delivery.

- [Analysis](analysis.md): current target, obsolete issue/closed PR, exact policy
  mismatches, required successor work and the missing maintainer/Trust CI outcome.
- [Issue draft](issue-draft.md): two target files, acceptance and validation commands.
- [Reproduction](reproduction.json): the existing focused unit passes; an independent
  AST inventory check fails specifically for the two missing Russian routes. This
  does not represent full target verification or a browser run.
- [Source manifest](source-manifest.json): three immutable remote blob identities.
  Private target source copies remain in external local cache; they are not included
  in this control repository. Cache paths are historical observations. A fresh clone
  can fetch the exact source URLs/SHAs and verify their Git blob and SHA-256 digests.
- [Probe](inventory-probe.py.txt): inert source for that AST-only reproduction. Run a
  copy with Python and an exact target checkout path; it does not import target code.

The complete artifact hashes are in [index.json](index.json). The agent's analysis
predates the controller's focused reproduction; its statement that the analyst ran
no tests is accurate for that separate read-only subtask.

After #155, route a separate bounded successor profile/gate change. Keep the old
profile's historical evidence intact. The new issue, one provider invocation and
each candidate publication effect need their applicable exact authorization.
Target Trust CI onboarding and a factual outcome observer are separate prerequisites
for `merged_accepted`; a draft alone cannot qualify the full external pilot or M8.

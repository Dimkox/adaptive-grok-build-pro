# v2.0.16 release sync

Makes repository identity truthful after the L5 union landing (#75), evidence merge (#72) and hardening (#77):
VERSION/`__version__`/README/CHANGELOG/START_HERE/ROADMAP/HANDOFF -> 2.0.16 candidate;
`published_release` promoted to the actually-published v2.0.15 (all facts re-derived from tag, GitHub API and the
tracked packages/ assets); v2.0.14 demoted into `prior_published_releases`; the pilot record archived verbatim into
`delivered_change_history` so its ~30 assertions survive one repointed line; `local_candidate` opened as a pending
2.0.16 artifact slot whose zip pair is asserted ABSENT until the separate artifact-child commit adds it.
Test anchors move in the same commit (lockstep proof at /tmp/release-sync/lockstep-proof.py; parallel and serial
verification both green). No tag, artifact, or activation happens here: this PR is the R of the R->A release pattern.

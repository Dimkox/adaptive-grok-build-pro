# Release plan — v2.0.15 pilot capability

The source parent `R` contains the disabled-by-default operator-pilot capability, final documentation and deterministic local evidence, but no `2.0.15` package bytes. Build the `2.0.15` ZIP+sidecar from exact clean `R` in two private `--no-local --no-hardlinks` clones under `umask 077`, require byte-identical archives and sidecars, then create artifact child `A` by importing only `packages/adaptive-grok-build-pro-v2.0.15.zip` and its `.sha256` sidecar. Run the one exact-head verifier and review wave on `A`; keep exact `R`/`A`/tree/archive identities in ignored runtime evidence and the delivery report so no post-artifact documentation commit forces another rebuild.

Push the feature branch and create a control-repository PR only under new exact grants, then merge only after the App-owned exact-SHA Trust CI check and GitGuardian pass. Tag/release the exact merged commit only under separate exact grants. Until then, the local `2.0.15` pair is unpublished and `v2.0.14` remains the latest published release.

After the control release, create/select one real landing issue and run one live pilot from the exact release source. Branch push and draft PR require separate operation-digest grants. The landing PR remains `merge_eligible=false` if its App-owned Trust CI profile/protection is absent. No automatic merge, deployment, M8 activation or M9 qualification follows.

Go: exact local evidence passes; control PR exact-head checks pass; release artifact identities match; live prerequisites and grants are exact. No-go: sandbox or credentials unavailable, target/issue/base drift, validation non-pass, external ambiguity, or missing independent landing gate.

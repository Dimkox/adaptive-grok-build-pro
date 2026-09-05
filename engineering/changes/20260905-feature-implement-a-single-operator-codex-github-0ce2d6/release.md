# Release plan — v2.0.15 pilot capability

The source release contains the disabled-by-default operator-pilot capability and deterministic local evidence. Build the `2.0.15` ZIP+sidecar only from the clean exact reviewed HEAD in two private `--no-local --no-hardlinks` clones under `umask 077`; import only matching artifacts. Push the feature branch, create a control-repository PR, and merge only after the App-owned exact-SHA Trust CI check and GitGuardian pass. Tag/release the exact merged commit only under exact grants.

After the control release, create/select one real landing issue and run one live pilot from the exact release source. Branch push and draft PR require separate operation-digest grants. The landing PR remains `merge_eligible=false` if its App-owned Trust CI profile/protection is absent. No automatic merge, deployment, M8 activation or M9 qualification follows.

Go: exact local evidence passes; control PR exact-head checks pass; release artifact identities match; live prerequisites and grants are exact. No-go: sandbox or credentials unavailable, target/issue/base drift, validation non-pass, external ambiguity, or missing independent landing gate.

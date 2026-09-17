# Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

`PROJECT_STATE.runtime_observations`: services gains omni (facts mirrored in the dossier `runtime-observation-omni-activation.json` inside the SR package's evidence directory, next to its predecessor); evidence pointer and observed_at advance; source_base deliberately remains the v2.0.18 tag target, matching observed_main_sha. Untouched: published_release/prior lists, operational_qualification, local_candidate flags, source_defaults, template, product code, contracts. The dossier records the incident (root-owned .git/index → failed validate_source start → chown restored to the installer-documented invariant) and the note that the shared-source repair covers all three units and only a future root git touch could regress it.

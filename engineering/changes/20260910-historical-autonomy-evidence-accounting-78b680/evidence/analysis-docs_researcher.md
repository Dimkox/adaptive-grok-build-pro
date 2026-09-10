# Documentation research: transferable evidence requirements

Route: `78b680187560`. Role: `docs_researcher`. Method: read-only comparison of source documentation and artifact provenance, retaining detailed findings privately.

Documents can describe validation, independent review or deployment without establishing an accepted business task. Keep the type and provenance of each claim explicit. Platform review records, repository-local review reports and authenticated acceptance evidence serve different purposes; one cannot substitute for another.

Deployment claims do not establish reproducible artifact proof. Reproducibility, cold-start readiness and rollback claims need evidence bound to the exact tested and deployed artifact. Recovery changes outside that artifact require a fresh artifact and corresponding verification before those claims can be supported. Historical documents do not establish current live-environment state.

Account type `User` cannot identify who personally performed a merge or recovery action. Operator-intervention counts and duration require attributed events and defined coverage windows. Missing acceptance, intervention, cost, latency, quality or failure measurements remain unknown rather than inferred from narrative success claims.

Qualification reconstruction requires source-bound task/run mapping, contemporaneous profile revisions, acceptance and audit evidence, exact-head attestation and currentness, measurement coverage and valid observation windows. Functional product delivery must remain visible while task-class compatibility and autonomy qualification are assessed separately.

Public documentation exports these reusable evidence requirements. Detailed inventories, deployment events, private recovery history and source-specific conclusions remain in the private artifact store. A historical accounting report grants no operational authority.

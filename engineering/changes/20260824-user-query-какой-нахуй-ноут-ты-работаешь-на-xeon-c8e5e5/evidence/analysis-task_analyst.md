# Analysis — task_analyst

Route `c8e5e567a15d`. Write owner `general_implementer`. Read-only. No push.

## Verdict

This message **names the M0.1 host as `claw`**. User already approved M0.0 plus host-activation intent; M0.1 was deferred only until a hostname. `claw` is that name (Xeon E5-2680 v4, 16 GiB ECC, chassis desktop). Override `analysis-docs_researcher.md`: do not treat `claw` as a forever-disqualified workspace, and do not rewrite Forbidden as “using host claw as the CI host.”

## Outcome

M0 spec, plan, and activation report retract the “laptop” misnomer and record hostname `claw`. Do **not** `compose up` this turn (`:8080` is still SearXNG). Compose-up stays a later `migration_or_external_write_approval` grant.

## In scope (docs only)

- Spec Host + Untrusted + Forbidden: drop “this laptop”; name `claw`; keep SearXNG/`n8n`/DinD/HTTPS as **compose-up** constraints, not a host-un-naming.
- Plan M0.1: named host is `claw`; drop “host name is still required.”
- Activation report: `Dedicated CI host (hostname only)` = `claw`. Other fields stay `UNKNOWN`.

## Out of scope

`docker compose up`, webhook, PEM/JWT, `branch-protect`, M0.2/M0.3, DARK_FACTORY/QUICKSTART “laptop”, historical package `372269`.

## Acceptance

Spec/plan contain `claw` and do not call this host a laptop. Plan no longer blocks on an unnamed host. Activation host field is `claw`. Characterization test covers those strings; `test_m0_invariants` stays green. No Trust CI containers; `:8080` remains SearXNG.

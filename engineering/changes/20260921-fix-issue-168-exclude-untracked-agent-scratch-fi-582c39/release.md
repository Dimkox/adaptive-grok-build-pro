# Source delivery

The user explicitly requested all remaining issue fixes; the coordinator adopted these bounded designs. The route has no named human gate. Local implementation and evidence are authorized; external writes, publication, merge, tag, release and deployment retain separate exact-operation authorization and external Trust CI requirements. Baseline: frozen PR170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48.

This is source-PR delivery, not a product-version, tag or GitHub Release operation. The sole product writer is integration_implementer. Go when all acceptance cases pass, full PR verification succeeds and selected independent reports/receipts bind the final fingerprint. No-go on hidden source/config changes, uncertain-path exclusion, scratch-only instability or stale evidence. External App-owned policy-epoch checks and required signed scopes must bind the current PR head before merge.

Observable success/failure: Fingerprint equality under untracked scratch churn and inequality under tracked, configuration and ordinary source changes; conservative inclusion under Git uncertainty. All shared local callers receive the utility change; refresh final-tree local receipts. No deployed policy or persisted schema rollout is required.

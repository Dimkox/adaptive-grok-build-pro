# Architecture

1. **Commercial = product bar, not a store.** MIT + free + public stay. No billing.
2. **Word-boundary risk terms.** `_risk` must not treat `продукт` as `прод`. Keep `прод упал` / `production` high.
3. **Do not publish.** Classifier false positive is not a production gate.

Parent writes: the user already specified the product identity.

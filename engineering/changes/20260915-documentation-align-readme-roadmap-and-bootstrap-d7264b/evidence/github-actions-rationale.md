# GitHub Actions rationale: source check on 2026-09-15

The user corrected cost and MIT explanations during this delivery. The repository prohibition is an architectural choice to keep deployed policy, holdout and signing authority outside a pull request, with exact-SHA and GitHub App source binding. It is not a claim that secure GitHub Actions configurations are impossible.

- GitHub confirms free standard GitHub-hosted runner usage for public repositories and free self-hosted runner usage: https://docs.github.com/en/billing/concepts/product-billing/github-actions . Private plan minute allowances do not cap public standard-runner minutes; storage and larger-runner pricing are separate.
- GitHub documents selecting an expected GitHub App for required status checks, because write-capable actors/integrations can set checks: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches .
- MIT governs permitted uses of the software and does not prohibit a CI provider: https://opensource.org/license/mit . Actions usage has its own service terms: https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features .

No measured cost advantage is established for this project's external PostgreSQL/worker/runner stack. Operating and maintaining that stack is an explicit tradeoff. No price schedule or license policy is changed by this documentation correction.

# Repair local architecture checks for G

User approved narrow local checker repair and keeping G in2.1.1. Final approved delivery is TWO source PRs: combined A-F/H/heartbeat-watchdog, then G Trust CI; an artifact-only PR follows. Do not weaken FIT-TRUST-CI-SEPARATION for real mixed executable implementation.

Scope: architecture_fitness.py, architecture.py, existing test_architecture_fitness.py and test_architecture_model.py only, plus this change package. No rules/schema/deployed policy changes, secrets, branch protection, execution authority, production mutation or version/release bytes in H. G stays isolated.

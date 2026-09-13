# Architecture

No new components. Invariants move from test scope into production scope at the existing chokepoints: `landing_artifact.deploy_members_for_source` (single epoch resolver) and module import (self-check). The PDF worker protocol (strict JSON, rlimits, 20s deadline) is unchanged; only test coverage of the real child is added. Governance assertions read the existing `ARCH.contract_inventory` snapshot pipeline.

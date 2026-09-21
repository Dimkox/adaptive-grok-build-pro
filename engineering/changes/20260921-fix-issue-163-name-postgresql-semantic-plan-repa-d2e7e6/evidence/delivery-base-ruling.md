# Issue 163 delivery base ruling — September 21, 2026

The initial full PR run at `b4ff8e3e7a30ba8c85679c2763f209452be5d420` failed. Unit, PostgreSQL, lint, coverage and source-stability checks passed; architecture fitness and dependent governance did not. Preserve that result as failure.

The original route `d2e7e68e7bd5` was generated before PR170 merged and retains base `90078959ff816068af374ad42f4bb80fdbaec866`. Its changed-code budget therefore includes issue155's already-delivered server/restart/SQL021 changes: factory-test complexity601 exceeds600 and803562bytes exceeds775000. PR170 delivered those changes to actual main `839d3aa26bc90417424d814ee48d8b5cd3be367e`; that exact main is already an ancestor of the issue163 branch.

A separate diagnostic using that actual main passes all unchanged architecture fitness rules. It is only a diagnostic, never a replacement verification receipt. No rule, threshold, deployed policy, migration or product code was changed to obtain it.

Continue this same isolated branch through a newly generated current-main delivery route. Adopt the existing issue163 implementation and analysis with exact source identity, retain this original package and failed evidence, and run a fresh complete PR gate and selected independent reviews. The old route is not rewritten or described as passing. No external CI or closure is authorized by this local diagnostic.

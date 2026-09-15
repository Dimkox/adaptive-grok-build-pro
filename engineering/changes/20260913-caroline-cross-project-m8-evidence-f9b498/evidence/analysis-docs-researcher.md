# docs_researcher: independent source facts

Route `f9b49845f0f6`; observed 2026-09-13 via read-only gh API/CLI and git on claw. Factory worktree HEAD `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`, origin `https://github.com/Dimkox/adaptive-grok-build-pro.git`. Current route selects docs_researcher for analysis, general_implementer as sole writer, and code_reviewer after verification. This report is evidence only, not merge or M8 activation authority.

## Independently observed GitHub identity

- Repository: https://github.com/kostiakhait/caroline ; public, not archived, default branch main.
- https://github.com/kostiakhait/caroline/issues/10 OPEN: [P1] Disconnect during forced compaction hides the resumed user answer.
- https://github.com/kostiakhait/caroline/issues/11 OPEN: [P2] Usage-cap one-shot follow-up rearms itself on repeated cap replies.
- https://github.com/kostiakhait/caroline/issues/12 OPEN: [P2] Splash readiness accepts empty disconnected tabs before restore completes.
- All three issue bodies pin audited source `9196c1a1bfca3248a1e42f2f69b890ff80ebef6e` and explicitly describe isolated reproduction limits.
- https://github.com/kostiakhait/caroline/pull/13 OPEN, DRAFT, title "Fix session recovery, usage-cap follow-up, and splash readiness"; head branch `codex/fix-issues-10-12`, exact head `1013c79e0a6426bf2d71d344d4dbd6869b0f71fe`; base main at `9196c1a1bfca3248a1e42f2f69b890ff80ebef6e`.
- PR contains one commit (2026-09-13T11:50:01Z), seven changed files: App.xaml.cs, MainWindow.xaml.cs, SplashReadiness.cs, Test-SplashReadiness.ps1, chat_session.py, main.py, test_session_regressions.py.
- Exact-head check-runs API returned total_count=0; combined commit status returned state=pending,total_count=0; PR statusCheckRollup empty. This is absence of reported checks, NOT a successful check, approval, or merge.

## Evidence and test limits

Issue #10 reports actual-method/stream control-flow reproduction with inert SDK callbacks: answer suppressed, real turn still pending. Issue #11 reports an AST/inert-timer reproduction with three follow-ups/four timers; monetary charges are explicitly not claimed. Issue #12 reports a C# source-predicate reproduction: disconnected empty tabs accepted; actual full-WPF visual consequence is source-derived, not experimentally demonstrated.

PR body claims five focused Python regressions, seven production-predicate C# cases using PowerShell Add-Type, compileall and git diff --check. It explicitly says full WPF build and live SDK/UI integration were unavailable because .NET SDK was absent and requests Windows validation before merge. Independently inspected exact-head test files via GitHub Contents API: Python source contains five test_ methods (lines 96,163,236,352,412); PowerShell contains seven cases (lines 11–17) and compiles only SplashReadiness.cs after widening its visibility in memory. I did not rerun these tests in this analysis. Therefore distinguish source-confirmed test presence and PR-reported passing results from independently rerun or full-system validation.

## Factory route lineage found on claw

- Original Caroline read-only audit route `f7f29515a2a8`, package `20260911-read-only-audit-review-of-kostiakhait-caroline-c-f7f295`, under `/home/pall/grok-projects/caroline-factory-audit-20260911/engineering/changes/`.
- Follow-up route `af819a589031`, package `20260913-read-only-security-review-and-audit-of-current-k-af819a`, same worktree. Both read-only routes select docs_researcher and have no write agent.
- Caroline fix route `ff76bf0a4d4d`, package `20260913-fix-caroline-issues-10-12-ff76bf`, same worktree; selected write agent general_implementer, code/test review required.
- These historical Factory route base commits are `be752872f3e5a9d6fe179872d9c8bdaec4338238`; they are FACTORY commit identities, not Caroline audited source identities.
- SEO audit precedent route `c9179d70b949`, package `/home/pall/grok-projects/seo-landing-factory-audit-20260913/engineering/changes/20260913-read-only-security-functionality-and-resilience-c9179d/route.json`, pins external `aleksandr-alhoff/seo-landing` source `1aa908f96a09e2e93fd1839ac51b02d362e7a8ef`. It authorizes read-only isolated audit and confirmed issue creation, with no target-code/Factory-product edits, deployment or merge. Factory base `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`.

## Classification recommendation

Index Caroline as factual cross-project audit plus draft-fix delivery evidence, explicitly non-qualifying for M8 activation or earned autonomy. GitHub issue publication and a draft PR demonstrate bounded observable work; they do not supply a frozen exact-profile cohort, activation record, independent exact-head acceptance, protected merge, production rollout, or full Windows integration validation. Existing START_HERE.md explicitly separates repository-delivered M8 source from operational cohort/activation evidence.

No source, dirty historical checkout, live service, token store or approval material was changed/read. Sole write is this requested analysis report in the active evidence package.

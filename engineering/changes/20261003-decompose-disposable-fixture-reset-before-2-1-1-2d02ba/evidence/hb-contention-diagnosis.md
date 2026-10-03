# Completed narrow HB diagnostic

Exact source: HBdc4062bcbc1e1da95cfe07077fc9cfbf273e0312. Factory has no diff versus63799f8760d3a55028d83ab5ff0116ececf8f7d1.234 copied source blobs positively match their exactGit identities before/after execution; originalHBHEAD and trackedtree unchanged. Private result: diagnostic-result.json; wrapper/probe/manifest/plan/capacity retained here. Source/candidate mutation:no. Full suite:no. One exactly boundPG17fixture onCPU14,15/max2; exactboundcontainerremoved. No repeat planned.

Five sequential exact-test trials:1PASS,2ERROR,3PASS,4PASS,5PASS. Each ran one existing unittest method, no skips. Trial2 had oneerror and no assertionfailures: LockNotAvailable propagated as StoreUnavailable. All childprocesses exited0 with valid sanitizedreports; no observer or wrapper error recorded. This is recurrence of the original two-reconciler test failure, not a new wrapper fault. The code/SQL/timeouts/acceptance assertions stayed unchanged; scratch-only claim-frame tracing and telemetry were added and may affect timing.

| Trial | Winner lock-hold→commit-return lower/upper bounds(ms) | Result |
|---|---:|---|
|1|41.10 /54.67|PASS|
|2|699.76 /714.69|ERROR: bounded lock refusal|
|3|148.60 /163.25|PASS|
|4|40.90 /54.44|PASS|
|5|42.55 /55.55|PASS|

Bounds are observational: row-lock acquisition occurs within recovery_context; the lower bound starts after it returned fulllockedcontext, the upper bound starts before its invocation. Return follows committed transaction. No fabricated exact acquisition timestamp.

Trial2 telemetry identifies winnerPID239 in COMMIT/IO/WalSync in57samples spanning643.71ms; loserPID240 in recovery_context/Lock/transactionid blockedby239 in46samples, then StoreUnavailable after~545.46ms from contextattempt. No cyclic blockers observed. This demonstrates commit durability wait extending counter-lock retention beyond the500mscontender bound. The cause of slowWalSync itself was not diagnosed. Original test's post-concurrency exact-once SQLassertion is unexecuted in this failing trial because executor.map propagates the exception first.

Controlled holder PASS: claimantPID357 positively blockedbyholderPID356. Lock retained600.17ms after confirmedwait; totalholder659.32ms<2sserver-side ceiling. Claim returned StoreUnavailable. Before retry terminalstage/job/claim/releaseevent/audit counts=[0,0,0,0,0]; run/allocation unreleased and capacityactivecount1. After holderrelease, unchanged claim retry returned a claim; counts=[1,1,1,1,1]. All rollback/retry assertions passed; no absent-wait/inconclusive condition. Retry lock-to-commit-return bounds47.10/61.14ms.

Runtime observations span18.714s. Exact wholefixtureelapsed was not separately recorded; plan creation→terminalreport is52s and provides an upper bound including launch coordination/installation/readiness. Cleanup completed before coordinator notification. No DSNs/passwords/SQLbodies/rawtracebacks/CLIarguments persisted or displayed.

Limits: one owned fixture, five instrumented trials and one controlledholder; no broadPGdiscovery, hostIO investigation, realservice qualification, independentreview or fullcandidatepass. The originalHBverification remainsfailed. Four narrow successes do not replace it; root owns any further interpretation/repair/verification decision.

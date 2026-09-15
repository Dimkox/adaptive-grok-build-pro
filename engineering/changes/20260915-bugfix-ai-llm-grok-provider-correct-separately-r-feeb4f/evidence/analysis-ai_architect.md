# AI architect — feeb4f381209

The root cause is P+C=T assumption and output=C. Captured response requires1336 input/1262 output; merely relaxing equality would undercount reasoning. For Grok only accept explicit valid additive T=P+C+R -> output C+R or inclusive T=P+C with0<=R<=C -> C. Reject unexplained residual, malformed counters, null explicit reasoning, bool/string/float/negative/excessive values. Absent/null detail container may retain legacy form but cannot explain residual; reject other non-object detail containers. Preserve arbitrary unrelated provider metadata. Cap derived output against existing local cap.

Keep Qwen nonstream and Omni unchanged, current model matching, raw digest, no retry/fallback and no reasoning text retention. Patch adapter1.1.1 and decoder identity together; retained v1/v2 evidence schema and digest domain remain unchanged. Analyst initially described global bump; controller bounded ruling selects Grok-only identity as required to keep Qwen digests stable.

Regression coverage includes captured sample, normalized evidence, absent/zero/inclusive reasoning, exact cap+one over, all invalid/missing forms, both Grok models, wrong model rejection, Qwen/SSE compatibility and retained evidence. Zero usage on failed attempts remains unavailable evidence, never a free-call claim; rejected-call accounting is separate scope.

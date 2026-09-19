# Local evidence for issue 152

- [Implementation and red/green results](implementation.md): exact commands, 13 selected methods before/after repair and 92 affected tests.
- [Controller verification](verification.json): one mandatory full invocation, passing product checks, and the isolated local Git-ref correction. The original nonzero invocation is retained explicitly; no full suite was repeated.
- Independent [code](review-code.md), [test](review-test.md) and [data](review-data.md) reviews: all PASS, with inspected file identities and limits.

The final local receipts are machine-local and bind the current commit/fingerprint. Tests remain applicable only while every verified product/test/config byte matches the saved manifest; package/report edits receive fresh cheap metadata, contract and privacy checks. External exact-head Trust CI remains the merge authority. These offline records establish no live Qwen acceptance.

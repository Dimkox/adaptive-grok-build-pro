# PR233 Trust CI diagnosis

The exact-head App check `110707979136` failed only `root-unittest`; both holdout lanes passed. The authenticated job log was unavailable (401). A correctly bound fresh clone at exact head `55779432d7ff13cc29a2c2cd9c72d69f5d45dda1` ran `python3 -m unittest discover -s tests -t . -q`: **995 tests PASS in 509.922s**.

One check-run and one exact-suite rerequest endpoint each returned GitHub 404; the tool-denial circuit breaker marks rerun blocked and forbids further retries. PR233 remains unmergeable until a fresh App-owned exact-head success exists.

# Release note

Local verification tooling; ships in whatever cycle merges it. On interpreters without pytest/xdist(/pytest-cov) the opt-in runner now degrades to one disclosed serial unittest pass instead of failing, which is what the no-pytest Trust CI image requires; with those modules present, pinned-version strictness is unchanged.

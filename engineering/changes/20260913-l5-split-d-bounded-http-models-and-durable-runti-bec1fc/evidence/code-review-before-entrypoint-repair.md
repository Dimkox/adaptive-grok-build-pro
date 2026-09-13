# Independent code review — split D, first frozen source

Verdict: FAIL. Two reproduced defects block approval of this immutable D source. The completed full verifier is passing evidence for its existing checks; it does not cover these failure cases. A/B/C review outcomes are unaffected.

## Exact reviewed identity

- Route: `bec1fcdde794`; change: `20260913-l5-split-d-bounded-http-models-and-durable-runti-bec1fc`.
- Source HEAD: `d1fdb7aec61b242c1a2fc5fc0ced1809e1b79c76`.
- Genuine route predecessor: `a75b3cd639a1483533069e8634759cdfc6612310`; actual PR predecessor is C `9ce156e0128b4f18b3fccfeca9a8edc7175da090` through subsequent merged documentation corrections.
- Independently recomputed clean-tree fingerprint: `ccc95dcd73e25b8a2ab1dbb21f6acaa23f43e03201a4af941b4fac1ff19ec379`.
- Independent reviewer: `code_reviewer`; sole source/test write owner: `data_implementer`.

Read the active route, reviewer role, requirements, architecture and test plan; inspected actual source diffs and surrounding implementation in HTTP profiles/exchange/credential selection, media/PDF/SSE parsing, normalization/runtime composition, private host helpers, settings, existing server startup/shutdown, SQLite initialization and writer ownership, direct server regression tests, and the 19-module architecture boundary inventory. The helper-only configuration module contains no future dedicated host loader. No E/F/G behavior was assumed.

## Blocking findings

### D-CR-1 — P2: double-slash anchors bypass declared runtime-root separation

Location: `factory/src/adaptive_factory/settings.py:105`–`115`; effect through `landing_server.py:24`–`60`.

`validate_landing()` accepts POSIX paths whose anchor is `//`, then compares roots lexically with `Path` equality/parents. On this Linux runtime, `/tmp/x/state` and `//tmp/x/state` identify the same directory but compare differently. The new direct durable composition therefore accepts state and quarantine roots pointing to one inode, contrary to the required disjoint-root boundary. The private-directory checks also use lexical repository/parent comparisons, and the quarantine store later resolves the alias. This is reachable through the D `FactorySettings`/existing-server entry point; a future dedicated E configuration loader does not protect it.

A bounded independent reproduction created only a private temporary control directory and state directory, passed the normal state path plus its `//` quarantine alias to default-off `compose_server_landing`, and obtained an actual owned SQLite runtime. The two configured roots had the same inode. No provider, source checkout, credentials or network request was involved.

```python
with TemporaryDirectory() as directory:
    root = Path(directory)
    control = root / "control"
    control.mkdir(mode=0o700)
    state = root / "state"
    state.mkdir(mode=0o700)
    alias = Path("/" + str(state))  # exactly two leading slashes
    settings = FactorySettings(
        database_url="", socket_path=root / "control.sock",
        actors_file=root / "actors.json",
        landing_state_path=state, landing_quarantine_path=alias,
    )
    settings.validate_landing()  # unexpectedly succeeds
    owned = compose_server_landing(settings, repository_root=control)
    assert state.stat().st_ino == alias.stat().st_ino
    owned.close()
```

Observed: `state/quarantine same inode True`, `composition accepted overlapping roots True`.

Required repair: reject the ambiguous `//` anchor in the shared `FactorySettings` landing-path validation before any I/O, and add direct settings/composition regression coverage for aliased roots. Retain all ordinary absolute-path and disjoint-root checks.

### D-CR-2 — P2: listener-close failure skips the newly owned SQLite cleanup

Location: `factory/src/adaptive_factory/server.py:246`–`254`.

The existing server's new shutdown block calls `listener.close()` before `owned_landing.close()` without an independent cleanup stage. If listener close raises, the owned SQLite connection/writer descriptor is not closed. In a failed startup/shutdown path where ASGI lifespan has not already released ownership, the advisory writer lock survives `main()` exit and prevents subsequent composition in that process. An integer descriptor is not automatically closed merely because the application object becomes unreachable.

A bounded failure injection used a real private temporary SQLite runtime, a listener mock whose close raises `OSError`, and mocked Uvicorn construction/run so no socket or server was started. After `server.main()` raised, an independent `SQLiteLandingJobStore` open returned `store_writer_active`. An explicit final cleanup in the reproduction released the lock.

```python
owned = compose_server_landing(settings, repository_root=control)
app = SimpleNamespace(state=SimpleNamespace(owned_landing_runtime=owned))
listener = Mock()
listener.close.side_effect = OSError("injected listener close failure")
try:
    with (
        patch.object(server.FactorySettings, "from_environment", return_value=settings),
        patch.object(server, "build_app", return_value=app),
        patch.object(server, "prepare_unix_socket", return_value=listener),
        patch.object(server.uvicorn, "Config"),
        patch.object(server.uvicorn, "Server"),
    ):
        try:
            server.main()
        except OSError:
            pass
    SQLiteLandingJobStore(settings.landing_state_path, repository_root=control)
    # Unexpectedly raises LandingServiceError(code="store_writer_active").
finally:
    owned.close()
```

Observed: `OSError injected listener close failure`, `writer lock after main exit store_writer_active`.

Required repair: make listener cleanup, owned-runtime cleanup and the applicable socket cleanup independent, preserving the appropriate startup/cleanup exception behavior. Add a real-writer-lock regression through this existing `server.main` entry point. The dedicated host's later cleanup implementation is outside D and cannot substitute for this fix.

## Other inspected boundaries and existing evidence

The actual D boundary inventory is 19 modules: 16 offline helpers/core/worker files, the SQLite store, the server composition module and the one network-bearing live-executors module. The new HTTP DTO/profile module itself has no network import. Qwen profiles bind region/model/media/streaming identity; the private assignment parser reads data without evaluating shell input. HTTP exchange is bounded by one whole-operation deadline and response limits, disables ambient proxy configuration and redirects, and has no retry path. The transport accepts a final single-choice text result with consistent usage; the SSE parser bounds bytes/lines/events and final ordering. PDF child-process cleanup uses independent ExitStack callbacks; duplicate case-folded DOCX members and invalid output Unicode have explicit guards.

The disclosed SQLite cleanup correction was inspected separately: acquisition closes its descriptor on post-flock interruption; failed connect/configure initialization handles BaseException and releases the writer even when connection close raises. `test_landing_server.py` contains real ownership/reopen assertions and injections for these stages. The new findings concern shared path configuration and the outer existing-server cleanup, not those already repaired constructor hunks. No schema migration or SQL-layout change was found in the SQLite delta.

`/tmp/agbp-sweep/split-d-full-final.json` reports PASS and binds the exact HEAD and fingerprint above; every recorded mandatory check passes, including architecture/governance, 653 core tests, factory and PostgreSQL verification, coverage and source stability. No full suite was rerun by this reviewer. The initial second reproduction attempt with system Python failed to import Uvicorn; it was rerun successfully using the repository's existing `/tmp/agbp-venv/bin/python`. That environment setup failure is not product failure evidence.

## Disposition and limits

Root was notified of both concrete reproductions. The source remains owned by `data_implementer`; this reviewer changed no application/test/repository source and performed no external write. The review stops with FAIL and does not certify every unexamined test branch. After minimal repairs, a new immutable identity, required verification and renewed independent review are necessary. This report deliberately remains bound to the old source above; it must not be reused as approval for a corrected tree. No external exact-SHA Trust CI or merge authority is asserted.

## SHA-256 inventory of the reviewed product/test delta at the exact HEAD

- `architecture/rules.yaml`: `30d11d294c1a4336633f9d1c80ddaa859b43e271d8dff65743f99ba6df0d4d45`
- `architecture/system.yaml`: `a9eb0db56d01021d2b5052d448f9d5b5f65e8dc67709f4153f8cfe0e38c3b21b`
- `factory/pyproject.toml`: `7821d3485cbd1fd6f9a7d1842a07ac692fa2386f60c88ac57f30019bff566b55`
- `factory/src/adaptive_factory/landing_host_config.py`: `ab1cc6e1f29b2f9a710b63f3ee84082ba39d6e1b0cfd15f29fff6f3564dfe00d`
- `factory/src/adaptive_factory/landing_http.py`: `ad1ec53d953df1e383f17acb0d7effeac7152cd3da5cb9bdeb2b5f4527abe55f`
- `factory/src/adaptive_factory/landing_intake.py`: `b7e19e75a0014be85b098bb8c9b4bdd0b5b87def83ffd5e3e47a43db13f0cc19`
- `factory/src/adaptive_factory/landing_live_executors.py`: `bc5d65baac30e8b0447c965df89af2a73f29627025955ef60e01552ed527a620`
- `factory/src/adaptive_factory/landing_media.py`: `fde1e88a2b22edc58b598b8ec4a5ddda14414cd78e93dfe9e01303fb44cf8efa`
- `factory/src/adaptive_factory/landing_normalizer.py`: `9efc109b97d8769f5ea347752edbe6ccc632c63521275f95bb3a54893c6c2e96`
- `factory/src/adaptive_factory/landing_runtime.py`: `22a8f6996096d495157dd5b9a7b21cbceeb1691c6ed27310296326d64f3af533`
- `factory/src/adaptive_factory/landing_server.py`: `c29e34644d20d8fb8ce4edcb74070310da8aaddfab9795b3ebaa5cb9838f70b8`
- `factory/src/adaptive_factory/landing_sqlite_store.py`: `7b9e677d1d1b04a87b62a2c985be026c71420c64eb559bab9d5fb6bb3f44806a`
- `factory/src/adaptive_factory/landing_sse.py`: `e9b92b75601d67aaf478c1f7bf702578c223773156d3cc4b6883821f00c75861`
- `factory/src/adaptive_factory/resources/landing_pdf_worker.py`: `55d527a6fbaa3e54340cb0fba9764c4b3682610b38c6b4d7555304b9432454ae`
- `factory/src/adaptive_factory/server.py`: `0ffd557e7e33c9b9fefc541f394c791ae1c6563dc45a6363871da49df8dffe7e`
- `factory/src/adaptive_factory/settings.py`: `78c2b5f91edc08bf18bff58ad25a26749097c38022fbba3a1890cbc1bfe29a5b`
- `factory/tests/test_landing_live_executors.py`: `3e8ac9c037309b14c154359098d9de5fd6ffb1220f67d3e7e7ff8e972d1afa67`
- `factory/tests/test_landing_media.py`: `39cfc6a4d491e00eba2d4db7c101cd1d2d4747c5b07d4b7276641c256a5ab7d3`
- `factory/tests/test_landing_normalizer.py`: `f267dd1ee0856b375b1c2b805d998a4eea4c5f0c048af256863cd0edbe86462f`
- `factory/tests/test_landing_server.py`: `d186a9e0ee262f872f07c57798c5c0f68f389cb1e1904b500ed0dea6110fc0c5`
- `factory/tests/test_landing_sse.py`: `9218d4cbde9c7ce11e9e27ed38ade06ad1c61aa9616844e4ac5bf5b5e36d3e67`
- `factory/tests/test_server.py`: `de267f7d063326310bf60004cf4bf5e205bb57d4032937a37fd8a58e5f969d68`
- `factory/uv.lock`: `27e8a6001da8598cb0765412e07b4ae9112b69b621b23a8d4f8c0ae0a10b0c28`
- `tests/test_landing_architecture_boundaries.py`: `5df7246f54b7d8ad48e215e93297daabe6a036973f00df03cf94615316ba26b3`

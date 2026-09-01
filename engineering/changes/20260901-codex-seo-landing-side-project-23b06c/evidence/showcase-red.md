# RED evidence — static showcase

Observed: 2026-09-01

The target directory was created empty, then the focused showcase contract was
run before implementation:

```bash
mkdir -p side-projects/seo-landing-showcase
python3 -m unittest tests.test_seo_landing_side_project.SeoLandingShowcaseContractTests -v
```

Observed result: exit code `1`.

```text
test_static_noindex_boundary ... ERROR
FileNotFoundError: [Errno 2] No such file or directory:
'.../side-projects/seo-landing-showcase/index.html'
Ran 1 test in 0.005s
FAILED (errors=1)
```

This is the expected RED state: the contract became active once the showcase
directory existed and failed because no product file had been implemented.

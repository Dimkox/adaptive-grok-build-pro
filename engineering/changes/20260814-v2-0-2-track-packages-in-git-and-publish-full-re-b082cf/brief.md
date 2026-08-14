# v2.0.2: track packages in git and publish full release

User asked for a complete git tree with the release and packages, then publish.

- Track versioned zips under `packages/`
- Bump to 2.0.2 (2.0.1 already tagged)
- Push `main`, tag `v2.0.2`, GitHub Release with zip + sha256 + source tar.gz
- Do not commit `.env`

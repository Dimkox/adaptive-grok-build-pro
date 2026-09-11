# Clean working tree to published 2.0.10

User: «вычисти и оставь только 2.0.10 в гите» after a status that showed `v2.0.10` @ `975ccb2` plus dirty session paperwork.

## Ruling

Make `git status` clean on committed `v2.0.10` (`975ccb2`). Do not create a new commit. Do not delete published tags, GitHub Releases, historical zips, CHANGELOG sections, or tracked change packages.

Those published objects are the history of 2.0.10. Deleting remote tags is irreversible and out of this feature route. Removing tracked zips would create a new untagged commit and stop being “only 2.0.10”.

## In

- Restore the 3 dirty tracked `state.json` files to HEAD
- Delete untracked leftover evidence under sibling `engineering/changes/*`
- Leave this new change package uncommitted (or it dirties the tree again)

## Out

- `git push --force`, history rewrite
- `git tag -d` / `git push origin :refs/tags/v2.0.*` except nothing about v2.0.10
- `gh release delete`
- Deleting `packages/…v2.0.0`–`v2.0.9.zip*`
- Bumping VERSION / retagging

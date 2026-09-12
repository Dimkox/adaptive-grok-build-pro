#!/bin/sh
# Source-only installer. Run only after exact operational approval; never starts
# a service, fetches Git remotes, reads credentials, or changes hosting config.
set -eu
umask 077
if [ "$#" -ne 3 ] || [ "$(id -u)" -ne 0 ]; then
    echo 'usage (root): install-claw.sh CONTROL_CHECKOUT LANDING_CHECKOUT EXACT_CONTROL_SHA' >&2
    exit 2
fi
control_checkout=$(realpath -e -- "$1")
landing_checkout=$(realpath -e -- "$2")
control_sha=$3
case "$control_sha" in *[!0-9a-f]*|'') exit 2 ;; esac
[ "${#control_sha}" -eq 40 ] || exit 2
landing_sha=fde60e040167c10975b00d11f578c4da6763069a
landing_tree=21817e70e079b772e1f3114a80dfc0320d1ada91
release_root=/opt/adaptive-l5/releases/$control_sha
source_root=/opt/adaptive-l5/sources/$landing_sha
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0
# Use fixed git argument lists. Local clones retain independent .git databases;
# archives and linked worktrees are not source snapshots for this runtime.
[ -d "$control_checkout/.git" ] && [ ! -L "$control_checkout/.git" ]
[ -d "$landing_checkout/.git" ] && [ ! -L "$landing_checkout/.git" ]
[ "$(git -c "safe.directory=$control_checkout" -C "$control_checkout" rev-parse HEAD)" = "$control_sha" ]
[ "$(git -c "safe.directory=$landing_checkout" -C "$landing_checkout" rev-parse HEAD)" = "$landing_sha" ]
[ "$(git -c "safe.directory=$landing_checkout" -C "$landing_checkout" rev-parse 'HEAD^{tree}')" = "$landing_tree" ]
[ -z "$(git -c "safe.directory=$control_checkout" --no-optional-locks -C "$control_checkout" status --porcelain --untracked-files=normal)" ]
[ -z "$(git -c "safe.directory=$landing_checkout" --no-optional-locks -C "$landing_checkout" status --porcelain --untracked-files=normal)" ]
if getent passwd adaptive-l5 >/dev/null; then
    [ "$(getent passwd adaptive-l5 | cut -d: -f6)" = /var/lib/adaptive-l5 ]
else
    useradd --system --user-group --home-dir /var/lib/adaptive-l5 --no-create-home --shell /usr/sbin/nologin adaptive-l5
fi
install -d -m 0755 /opt/adaptive-l5 /opt/adaptive-l5/releases /opt/adaptive-l5/sources
# Immutable release names are never replaced. Preserve a failed partial install.
mkdir -m 0755 "$release_root"
git -c "safe.directory=$control_checkout" -c protocol.file.allow=always clone --no-local --no-hardlinks --no-checkout -- "$control_checkout" "$release_root/repository"
git -C "$release_root/repository" checkout --detach "$control_sha"
git -C "$release_root/repository" remote set-url origin https://github.com/Dimkox/adaptive-grok-build-pro.git
if [ ! -e "$source_root" ]; then
    git -c "safe.directory=$landing_checkout" -c protocol.file.allow=always clone --no-local --no-hardlinks --no-checkout -- "$landing_checkout" "$source_root"
    git -C "$source_root" checkout --detach "$landing_sha"
    git -C "$source_root" remote set-url origin https://github.com/Dimkox/ai-dark-factory-landing.git
    chown -R adaptive-l5:adaptive-l5 "$source_root"
fi
# The service user must own its real source .git, which systemd exposes read-only.
runuser -u adaptive-l5 -- git --no-optional-locks -C "$source_root" rev-parse HEAD > "$release_root/source-head.txt"
[ "$(cat "$release_root/source-head.txt")" = "$landing_sha" ]
[ "$(runuser -u adaptive-l5 -- git --no-optional-locks -C "$source_root" rev-parse 'HEAD^{tree}')" = "$landing_tree" ]
[ -z "$(runuser -u adaptive-l5 -- git --no-optional-locks -C "$source_root" status --porcelain --untracked-files=normal)" ]
python3 -m venv "$release_root/venv"
"$release_root/venv/bin/python" -m pip install "$release_root/repository/factory" "$release_root/repository/delivery"
chmod -R a+rX "$release_root/repository" "$release_root/venv"
for directory in /var/lib/adaptive-l5 /var/lib/adaptive-l5/state /var/lib/adaptive-l5/quarantine /var/lib/adaptive-l5/scratch /var/lib/adaptive-l5/artifacts /var/lib/adaptive-l5/publication /var/lib/adaptive-l5/backups; do
    if [ ! -e "$directory" ]; then install -d -o adaptive-l5 -g adaptive-l5 -m 0700 "$directory"; fi
done
if [ ! -e /etc/adaptive-l5 ]; then install -d -o adaptive-l5 -g adaptive-l5 -m 0700 /etc/adaptive-l5; fi
sed "s/REPLACE_EXACT_CONTROL_SHA/$control_sha/g" "$release_root/repository/factory/runtime/landing-host.example.json" > "$release_root/landing-host.json"
chown adaptive-l5:adaptive-l5 "$release_root/landing-host.json"
chmod 0600 "$release_root/landing-host.json"
# read_private_file requires the immediate config parent to be service-owned.
chown adaptive-l5:adaptive-l5 "$release_root"
chmod 0755 "$release_root"
sed "s|@RELEASE_ROOT@|$release_root|g" "$release_root/repository/factory/runtime/adaptive-l5.service.in" > "$release_root/adaptive-l5.service"
chmod 0644 "$release_root/adaptive-l5.service"
echo "Inactive release prepared: $release_root"
echo 'Provision separate actors/tokens and the selected provider through the operator credential boundary.'
echo 'Installing the generated systemd unit, daemon-reload and start require separate exact activation authority.'

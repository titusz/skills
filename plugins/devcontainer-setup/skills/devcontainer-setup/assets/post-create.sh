#!/usr/bin/env bash
# In-container setup, run via postCreateCommand after the container is created.
# Every script is invoked through `bash` (never relying on the exec bit, which
# Windows bind mounts cannot preserve). Credential seeding degrades gracefully
# (reported, never fatal); a bootstrap failure is fatal — a container without
# toolchains is not ready.
set -uo pipefail

cd "$(dirname "$0")/.."

# Hand root-created paths back to the dev user before anything writes to
# them. The -O guard keeps repeat creates fast (no chown -R over warm caches).
. .devcontainer/owned-paths.sh
for d in $DEV_OWNED_PATHS; do
  [ -e "$d" ] || continue
  [ -O "$d" ] || sudo chown -R "$(id -un)":"$(id -gn)" "$d" 2>/dev/null || true
done

# Container-local git config: inherits host settings, overrides credential
# helpers to use the container's gh CLI.
bash .devcontainer/setup-gitconfig.sh

# Codex: seed the ~/.codex volume from the read-only host mount (non-fatal).
bash .devcontainer/setup-codex.sh \
  || echo "codex: setup failed (non-fatal) — run 'bash .devcontainer/setup-codex.sh' manually"

# Toolchains + project dependencies (shared with the Anthropic cloud
# bootstrap). A failure propagates below, after the doctor has reported.
bootstrap_status=0
bash .devcontainer/bootstrap.sh || bootstrap_status=$?

# Full health report — informational, never fails container creation itself.
bash .devcontainer/doctor.sh || true

if [ "$bootstrap_status" -ne 0 ]; then
  echo "post-create: FAILED — bootstrap exited $bootstrap_status (toolchains/dependencies incomplete); fix the error above, then re-run 'bash .devcontainer/bootstrap.sh'"
  exit "$bootstrap_status"
fi
echo "post-create: done"

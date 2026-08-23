#!/usr/bin/env bash
# In-container setup, run via postCreateCommand after the container is created.
# Every script is invoked through `bash` (never relying on the exec bit, which
# Windows bind mounts cannot preserve). Credential seeding degrades gracefully
# (reported, never fatal); a bootstrap failure is fatal — a container without
# toolchains is not ready.
set -uo pipefail

cd "$(dirname "$0")/.."

# Serialize concurrent runs: editors attach before postCreate finishes (the
# spec's default waitFor is updateContentCommand), so a doctor --fix or manual
# re-run can otherwise race the in-flight hook with two concurrent `mise
# install`s. The lock file is container-local, so it cannot go stale across
# rebuilds, and flock releases it if a run crashes. Without flock (customized
# image) runs proceed unserialized, as before.
if command -v flock >/dev/null 2>&1; then
  exec 9>/tmp/.post-create.lock
  if ! flock -n 9; then
    echo "post-create: another run is in progress — waiting for it to finish"
    flock 9
    if [ -e /var/tmp/.post-create-ok ]; then
      echo "post-create: the concurrent run completed successfully — nothing to do"
      exit 0
    fi
    echo "post-create: the concurrent run did not complete — continuing with this one"
  fi
fi

# Hand root-created paths back to the dev user before anything writes to
# them. The -O guard keeps repeat creates fast (no chown -R over warm caches).
# The source is guarded: under `set -u`, a transient bind-mount read error
# here would otherwise abort the whole orchestrator via the unbound variable —
# one failed read must degrade one step (doctor reports/repairs ownership
# later), never kill every setup step after it.
. .devcontainer/owned-paths.sh 2>/dev/null || true
DEV_OWNED_PATHS="${DEV_OWNED_PATHS:-}"
for d in $DEV_OWNED_PATHS; do
  [ -e "$d" ] || continue
  [ -O "$d" ] || sudo chown -R "$(id -un)":"$(id -gn)" "$d" 2>/dev/null || true
done

# Container-local git config: inherits host settings, overrides credential
# helpers to use the container's gh CLI.
bash .devcontainer/setup-gitconfig.sh

# Claude: merge sign-in state (oauthAccount + onboarding flag) from the
# read-only host mount into the container's .claude.json (non-fatal).
bash .devcontainer/setup-claude.sh \
  || echo "claude: setup failed (non-fatal) — run 'bash .devcontainer/setup-claude.sh' manually"

# Codex: seed the ~/.codex volume from the read-only host mount (non-fatal).
bash .devcontainer/setup-codex.sh \
  || echo "codex: setup failed (non-fatal) — run 'bash .devcontainer/setup-codex.sh' manually"

# Toolchains + project dependencies (shared with the Anthropic cloud
# bootstrap). A failure propagates below, after the doctor has reported.
bootstrap_status=0
bash .devcontainer/bootstrap.sh || bootstrap_status=$?

# Completion stamp: lifecycle hooks are editor-dependent and can be skipped
# silently, so the shell rc and doctor.sh warn while this stamp is absent
# (see references/design.md in the devcontainer-setup plugin). It lives on the
# container-local filesystem, never a volume: the container layer persists
# across stops/starts but not across rebuilds — exactly the stamp's required
# scope. A volume-persisted stamp could mask a rebuild whose create hook was
# skipped, and keying one to the hostname fails when runArgs pins --hostname.
if [ "$bootstrap_status" -eq 0 ]; then
  touch /var/tmp/.post-create-ok 2>/dev/null || true
else
  rm -f /var/tmp/.post-create-ok 2>/dev/null || true
fi

# Full health report — informational, never fails container creation itself.
bash .devcontainer/doctor.sh || true

if [ "$bootstrap_status" -ne 0 ]; then
  echo "post-create: FAILED — bootstrap exited $bootstrap_status (toolchains/dependencies incomplete); fix the error above, then re-run 'bash .devcontainer/bootstrap.sh'"
  exit "$bootstrap_status"
fi
echo "post-create: done"

#!/usr/bin/env bash
# Host-side pre-flight, run via initializeCommand before the container builds.
#
# The devcontainer bind-mounts ~/.claude, ~/.codex and ~/.gitconfig from the
# host. When a tool has never been set up on the host, those paths don't exist
# and Docker would either fail the mount or create the source as a root-owned
# directory. Creating empty stubs here makes the mounts succeed and lets the
# container start fresh. What flows back out of the container: Claude Code
# sign-ins land on the host ~/.claude mount (shared session, survives
# rebuilds); Codex logins and git identity persist in named volumes, not on
# the host.
#
# Works on Linux/macOS (HOME), Windows via Git Bash (HOME set by Git Bash),
# and Windows where `bash` resolves to the WSL launcher (see below).
set -e

home="${HOME:-$USERPROFILE}"

# On Windows, an unqualified `bash` often resolves to the WSL launcher rather
# than Git Bash. The mount sources still resolve the *Windows* %USERPROFILE%,
# so under WSL the stubs must target the Windows home, not the WSL one.
if grep -qi microsoft /proc/version 2>/dev/null && command -v wslpath >/dev/null 2>&1; then
  win_home="$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')"
  if [ -n "$win_home" ]; then
    home="$(wslpath "$win_home")"
    echo "init-host: WSL detected — initializing the Windows home ($win_home)" >&2
  fi
fi

# A HOME variable set machine- or user-wide on Windows breaks the
# ${localEnv:HOME}${localEnv:USERPROFILE} mount concatenation in
# devcontainer.json (both variables expand). Advisory only; the registry
# probe sees only globally-set variables, not this shell's own HOME.
if command -v reg.exe >/dev/null 2>&1; then
  if MSYS_NO_PATHCONV=1 reg.exe query 'HKCU\Environment' /v HOME >/dev/null 2>&1 \
    || MSYS_NO_PATHCONV=1 reg.exe query 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment' /v HOME >/dev/null 2>&1; then
    echo "init-host: WARNING — HOME is set globally in the Windows environment; mount sources will concatenate HOME+USERPROFILE into a broken path. Remove the global HOME variable." >&2
  fi
fi

mkdir -p "$home/.claude"
mkdir -p "$home/.codex"
[ -f "$home/.gitconfig" ] || touch "$home/.gitconfig"
# Claude Code keeps sign-in/account state in ~/.claude.json (separate from the
# ~/.claude dir); it is mounted read-only as a seed so the host sign-in carries
# into the container without a login prompt. Advisory like the checks below:
# a failed stub must not abort creation here — the mount itself will surface it.
if [ ! -e "$home/.claude.json" ]; then
  echo '{}' > "$home/.claude.json" \
    || echo "init-host: WARNING — could not create the ~/.claude.json stub; the read-only seed mount will fail" >&2
elif [ ! -f "$home/.claude.json" ]; then
  echo "init-host: WARNING — ~/.claude.json is not a regular file (leftover from an old mount?) — remove it so the sign-in seed can work" >&2
fi

# Advisory only — never fail: missing credentials just mean signing in inside
# the container instead of inheriting the host session.
[ -s "$home/.claude/.credentials.json" ] \
  || echo "init-host: no Claude Code credential file on host (normal on macOS, where tokens live in the Keychain) — run 'claude' inside the container to sign in" >&2
[ -s "$home/.codex/auth.json" ] \
  || echo "init-host: no Codex credentials on host — run 'codex login --device-auth' inside the container to sign in" >&2
if [ ! -s "$home/.gitconfig" ]; then
  if [ -s "$home/.config/git/config" ]; then
    echo "init-host: host git identity lives in ~/.config/git/config, which is not mounted — set it once inside the container (doctor.sh will guide you; it persists in the ~/.config volume)" >&2
  else
    echo "init-host: host ~/.gitconfig is empty — set git identity inside the container (doctor.sh will guide you)" >&2
  fi
fi

echo "init-host: ok"

#!/usr/bin/env bash
# Seed Claude Code sign-in state from the read-only host mount.
#
# Sign-in/account state (oauthAccount) and the onboarding flag live in
# ~/.claude.json, not in .credentials.json — without both, the interactive UI
# runs first-run onboarding including a login screen despite valid
# credentials. The host file is bind-mounted read-only at ~/.claude.json-host;
# this script merges ONLY those two fields into the container's live config at
# $CLAUDE_CONFIG_DIR/.claude.json, preserving everything the container has
# accumulated (trust dialogs, MCP servers, settings). A whole-file copy would
# import host-only settings that cannot work in the container — stdio MCP
# servers with host paths, installMethod, the projects/history map — the same
# hazard the Codex seed documents for config.toml.
#
# Deliberately NOT `set -e`: this is a convenience seeder, not a hard
# dependency — it always exits 0 so a hiccup can never abort post-create.

# Signed-in state = an account object (a signed-out "oauthAccount": null does
# not count) plus a completed onboarding flag. Single source of truth for the
# predicate — doctor.sh sources this file to reuse it.
claude_signin_state_ok() {
  grep -q '"oauthAccount": *{' "$1" 2>/dev/null \
    && grep -q '"hasCompletedOnboarding": *true' "$1" 2>/dev/null
}

# Executed directly (bash setup-claude.sh) → run the seed below. Sourced
# (doctor.sh reusing the predicate) → definitions only, stop here.
[ "${0##*/}" = "setup-claude.sh" ] || return 0

host="$HOME/.claude.json-host"
dst="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.claude.json"

if ! claude_signin_state_ok "$host"; then
  echo "claude: no sign-in state on the host mount — run 'claude' to sign in"
  exit 0
fi
if claude_signin_state_ok "$dst"; then
  echo "claude: sign-in state already present in container"
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  # Merge the two fields, retrying to ride out transient I/O errors on the
  # Windows->container bind mount.
  for attempt in 1 2 3; do
    if python3 - "$host" "$dst" <<'PYEOF'
import json, pathlib, sys

host, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
state = json.loads(host.read_text())
try:
    merged = json.loads(dst.read_text())
except (OSError, ValueError):
    merged = {}
if not isinstance(merged, dict):
    merged = {}
merged["oauthAccount"] = state["oauthAccount"]
merged["hasCompletedOnboarding"] = True
tmp = dst.parent / (dst.name + ".tmp")
tmp.write_text(json.dumps(merged, indent=2) + "\n")
tmp.replace(dst)
PYEOF
    then
      echo "claude: seeded sign-in state from host"
      exit 0
    fi
    sleep 1
  done
  echo "claude: WARNING — could not seed sign-in state after retries (bind-mount hiccup?) — fix: bash .devcontainer/doctor.sh --fix, or run 'claude' to sign in"
else
  # No python3 (customized image): a whole-file copy is only safe when there
  # is no container config to clobber, and it may import host-only settings
  # (see references/design.md in the devcontainer-setup plugin).
  if [ ! -s "$dst" ] && cp "$host" "$dst" 2>/dev/null; then
    echo "claude: seeded sign-in state from host (whole-file copy — python3 unavailable)"
  else
    echo "claude: state seed skipped (python3 unavailable, container config present) — run 'claude' to sign in"
  fi
fi

# Always succeed: a seeding hiccup must never abort the rest of post-create.
exit 0

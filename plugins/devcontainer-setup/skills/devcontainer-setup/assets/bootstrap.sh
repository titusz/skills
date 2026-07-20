#!/usr/bin/env bash
# Toolchain + dependency bootstrap, shared by two entry points:
#   - devcontainer postCreate (via post-create.sh)
#   - Anthropic cloud sessions (claude.ai/code) via the CLAUDE_CODE_REMOTE-
#     guarded SessionStart hook in .claude/settings.json — the cloud sandbox
#     ignores .devcontainer/, so this script is what makes the repo work there.
#
# All project specifics live in mise.toml ([tools] pins the toolchains,
# [tasks.setup] installs dependencies); this script stays generic and
# idempotent — re-runs are fast no-ops once everything is installed.
set -uo pipefail

export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:$PATH"

# Install mise when missing (pre-installed in the devcontainer image; the
# Anthropic cloud sandbox starts without it).
if ! command -v mise >/dev/null 2>&1; then
  echo "bootstrap: installing mise"
  curl -fsSL https://mise.run | sh || { echo "bootstrap: mise install FAILED"; exit 1; }
fi

if [ -f mise.toml ] || [ -f .mise.toml ] || [ -f .config/mise/config.toml ]; then
  mise trust --quiet 2>/dev/null || mise trust
  echo "bootstrap: mise install (toolchains from mise.toml)"
  mise install || { echo "bootstrap: mise install FAILED"; exit 1; }

  # Project dependencies — defined as the `setup` task in mise.toml.
  if mise tasks info setup >/dev/null 2>&1; then
    echo "bootstrap: mise run setup (project dependencies)"
    mise run setup || { echo "bootstrap: 'mise run setup' FAILED"; exit 1; }
  else
    echo "bootstrap: no 'setup' task in mise.toml — skipping dependency install"
  fi
else
  echo "bootstrap: no mise.toml found — nothing to install"
fi

echo "bootstrap: done"

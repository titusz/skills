#!/usr/bin/env bash
# Health check (and repair) for the devcontainer agent environment.
#
# Usage:
#   bash .devcontainer/doctor.sh          # report only
#   bash .devcontainer/doctor.sh --fix    # repair what can be repaired
#   mise run doctor                       # same, via the mise task
#
# Verifies the wiring this devcontainer promises: git identity + GitHub auth,
# Claude Code and Codex readiness (host-mounted credentials), mise toolchains,
# volume ownership, and project dependencies. Every problem is reported with
# the exact command that fixes it; --fix runs the safe repairs automatically.
# Also runs (with reduced checks) in Anthropic cloud sessions and on a bare
# host, so it can be a mise task without being container-only.
set -u

FIX=0
[ "${1:-}" = "--fix" ] && FIX=1

PASS=0; WARN=0; FAIL=0
ok()   { printf '  \xe2\x9c\x93 %s\n' "$1"; PASS=$((PASS+1)); }
warn() { printf '  ! %s\n' "$1"; WARN=$((WARN+1)); }
bad()  { printf '  \xe2\x9c\x97 %s\n' "$1"; FAIL=$((FAIL+1)); }
section() { printf '\n== %s ==\n' "$1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  MODE=cloud
elif [ "${DEVCONTAINER:-}" = "true" ]; then
  MODE=devcontainer
else
  MODE=host
fi

echo "doctor: mode=$MODE fix=$FIX root=$ROOT"

# --- setup scripts -----------------------------------------------------------
section "setup scripts"
CR="$(printf '\r')"
crlf_files=""
for f in "$SCRIPT_DIR"/*.sh; do
  [ -f "$f" ] || continue
  if grep -q "$CR" "$f" 2>/dev/null; then crlf_files="$crlf_files $f"; fi
done
if [ -n "$crlf_files" ]; then
  if [ "$FIX" = 1 ]; then
    # tr via temp file (not sed -i): portable across GNU/BSD sed and safe for
    # paths with spaces; only report success for files actually converted.
    converted=""; convert_failed=""
    for f in "$SCRIPT_DIR"/*.sh; do
      [ -f "$f" ] || continue
      grep -q "$CR" "$f" 2>/dev/null || continue
      if tr -d '\r' < "$f" > "$f.tmp" && mv "$f.tmp" "$f"; then
        converted="$converted $f"
      else
        rm -f "$f.tmp"
        convert_failed="$convert_failed $f"
      fi
    done
    [ -n "$converted" ] && ok "converted CRLF line endings to LF in:$converted"
    [ -n "$convert_failed" ] && bad "could not convert:$convert_failed — convert manually (tr -d '\\r')"
  else
    bad "CRLF line endings (break bash in the container):$crlf_files — fix: --fix, or add '.devcontainer/*.sh text eol=lf' to .gitattributes"
  fi
else
  ok "all .devcontainer scripts have LF line endings"
fi

# --- git ---------------------------------------------------------------------
section "git"
if command -v git >/dev/null 2>&1; then
  ok "git $(git --version | awk '{print $3}')"

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ok "workspace is a usable git repository (safe.directory ok)"
  else
    bad "git refuses this workspace — fix: git config --global --add safe.directory $ROOT"
  fi

  name="$(git config user.name || true)"
  email="$(git config user.email || true)"
  if [ -n "$name" ] && [ -n "$email" ]; then
    ok "identity: $name <$email>"
  elif [ "$MODE" = devcontainer ]; then
    # --global would land in the generated ~/.gitconfig, which is wiped on
    # every rebuild; ~/.config/git/config lives in a volume and is included.
    bad "git identity unset — fix: git config --file ~/.config/git/config user.name 'Your Name' && git config --file ~/.config/git/config user.email 'you@example.com' (persists in the ~/.config volume; host ~/.gitconfig was empty or not mounted)"
  else
    bad "git identity unset — fix: git config --global user.name 'Your Name' && git config --global user.email 'you@example.com'"
  fi

  if [ "$MODE" = devcontainer ]; then
    if git config --get-all credential.https://github.com.helper 2>/dev/null | grep -q "gh auth git-credential"; then
      ok "credential helper: gh auth git-credential"
    elif [ "$FIX" = 1 ] && [ -f "$SCRIPT_DIR/setup-gitconfig.sh" ]; then
      bash "$SCRIPT_DIR/setup-gitconfig.sh"
      if git config --get-all credential.https://github.com.helper 2>/dev/null | grep -q "gh auth git-credential"; then
        ok "re-ran setup-gitconfig.sh — credential helper configured"
      else
        bad "setup-gitconfig.sh ran but the gh credential helper is still missing — run 'bash .devcontainer/setup-gitconfig.sh' manually to see why"
      fi
    else
      bad "gh credential helper not configured — fix: bash .devcontainer/setup-gitconfig.sh"
    fi

    # Read outside the GIT_CONFIG_* containerEnv override (highest scope),
    # which would otherwise mask a host gpgsign=true in every invocation.
    if [ "$(env -u GIT_CONFIG_COUNT git config commit.gpgsign 2>/dev/null || true)" = "true" ]; then
      warn "commit.gpgsign=true — signing keys are usually absent in containers (devcontainer.json disables it via GIT_CONFIG_* env)"
    else
      ok "commit signing off in container"
    fi
  fi
else
  bad "git not installed"
fi

# --- github auth -------------------------------------------------------------
if [ "$MODE" = devcontainer ]; then
  section "github auth"
  if command -v gh >/dev/null 2>&1; then
    if gh auth status >/dev/null 2>&1; then
      ok "gh authenticated ($(gh api user --jq .login 2>/dev/null || echo account))"
    elif [ -n "${GH_TOKEN:-}" ]; then
      warn "GH_TOKEN is set but gh auth status failed — token may be expired"
    else
      warn "gh not authenticated — git push will fail; fix: export GH_TOKEN on the host before starting, or run 'gh auth login' (persists in the ~/.config volume)"
    fi
  else
    bad "gh CLI missing from image"
  fi
fi

# --- claude code -------------------------------------------------------------
section "claude code"
if command -v claude >/dev/null 2>&1; then
  ok "claude $(claude --version 2>/dev/null | head -1 || echo installed)"
else
  bad "claude not on PATH — image build problem; rebuild the container"
fi
if [ "$MODE" = devcontainer ]; then
  if [ -d "$HOME/.claude" ] && touch "$HOME/.claude/.doctor-write-test" 2>/dev/null; then
    rm -f "$HOME/.claude/.doctor-write-test"
    ok "~/.claude mounted and writable"
  else
    bad "~/.claude missing or read-only — check the bind mount in devcontainer.json"
  fi
  if [ "${CLAUDE_CONFIG_DIR:-}" = "$HOME/.claude" ]; then
    ok "CLAUDE_CONFIG_DIR points at the mounted ~/.claude (state survives rebuilds)"
  else
    warn "CLAUDE_CONFIG_DIR is not $HOME/.claude — container Claude state will not survive rebuilds; check containerEnv in devcontainer.json"
  fi
  if [ -s "$HOME/.claude/.credentials.json" ]; then
    ok "credentials present (host session carried over)"
  else
    warn "no credentials — run 'claude' to sign in (stored on the host mount, survives rebuilds)"
  fi
  # Host-side plugin marketplaces store Windows install paths that the
  # container plugin system cannot resolve.
  km="$HOME/.claude/plugins/known_marketplaces.json"
  if [ -f "$km" ] && grep -q '\\\\' "$km" 2>/dev/null; then
    if [ "$FIX" = 1 ] && command -v python3 >/dev/null 2>&1; then
      if python3 - "$km" <<'PYEOF'
import json, re, sys, os, pathlib
f = pathlib.Path(sys.argv[1])
data = json.loads(f.read_text())
home = os.environ["HOME"]
changed = False
for mk in data.values():
    loc = mk.get("installLocation", "")
    m = re.search(r"[/\\](plugins[/\\]marketplaces[/\\].+)$", loc)
    if m:
        new = home + "/.claude/" + m.group(1).replace("\\", "/")
        if new != loc:
            mk["installLocation"] = new
            changed = True
if changed:
    f.write_text(json.dumps(data, indent=2) + "\n")
    print("  rewrote marketplace installLocation paths for the container")
PYEOF
      then
        ok "plugin marketplace paths rewritten to container paths"
      else
        bad "marketplace path rewrite failed (malformed $km?) — inspect the file manually"
      fi
    else
      warn "plugin marketplace paths contain Windows separators — plugins may not load; fix: --fix"
    fi
  else
    ok "plugin marketplace paths look container-compatible"
  fi
fi

# --- codex -------------------------------------------------------------------
if [ "$MODE" = devcontainer ]; then
  section "codex"
  if command -v codex >/dev/null 2>&1; then
    ok "codex $(codex --version 2>/dev/null | head -1 || echo installed)"
  else
    bad "codex not on PATH — image build problem; rebuild the container"
  fi
  if [ -s "$HOME/.codex/auth.json" ]; then
    ok "credentials present in ~/.codex volume"
  elif [ -s "$HOME/.codex-host/auth.json" ]; then
    if [ "$FIX" = 1 ] && [ -f "$SCRIPT_DIR/setup-codex.sh" ]; then
      bash "$SCRIPT_DIR/setup-codex.sh"
      if [ -s "$HOME/.codex/auth.json" ]; then
        ok "re-ran setup-codex.sh — credentials seeded from host"
      else
        warn "setup-codex.sh could not seed credentials from the host copy — run 'codex login --device-auth' in the container"
      fi
    else
      warn "host has codex credentials but the volume does not — fix: bash .devcontainer/setup-codex.sh"
    fi
  else
    warn "no codex credentials — run 'codex login --device-auth' (stored in the volume, survives rebuilds)"
  fi
  if [ -f "$HOME/.codex/config.toml" ] && grep -q '^[[:space:]]*cli_auth_credentials_store[[:space:]]*=[[:space:]]*"file"' "$HOME/.codex/config.toml"; then
    ok "file-based credential storage configured"
  elif [ "$FIX" = 1 ] && [ -f "$SCRIPT_DIR/setup-codex.sh" ]; then
    bash "$SCRIPT_DIR/setup-codex.sh"
    if grep -q '^[[:space:]]*cli_auth_credentials_store[[:space:]]*=[[:space:]]*"file"' "$HOME/.codex/config.toml" 2>/dev/null; then
      ok "re-ran setup-codex.sh — file-based credential storage configured"
    else
      warn "cli_auth_credentials_store is still not \"file\" after setup-codex.sh — edit ~/.codex/config.toml manually"
    fi
  else
    warn "cli_auth_credentials_store != \"file\" — keyring storage does not survive rebuilds; fix: bash .devcontainer/setup-codex.sh"
  fi
fi

# --- gpu ---------------------------------------------------------------------
# Self-activating: runs only when the project's devcontainer.json requests a
# GPU (hostRequirements.gpu, or a locally added --gpus flag). CPU-only is a
# supported degradation for "optional" GPUs, and passthrough is host-side, so
# absence warns instead of failing and --fix has nothing to repair here.
if [ "$MODE" = devcontainer ] && grep -q '"gpu"\|--gpus' "$SCRIPT_DIR/devcontainer.json" 2>/dev/null; then
  section "gpu"
  if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
    if [ -n "$gpu_name" ]; then
      ok "GPU passed through: $gpu_name"
    else
      warn "nvidia-smi present but not responding — update the host NVIDIA driver, then rebuild the container"
    fi
  else
    warn "no GPU in container (CPU-only) — host needs the NVIDIA driver (plus nvidia-container-toolkit on Linux; Docker Desktop bundles it) and a launcher that honors hostRequirements.gpu"
  fi
fi

# --- mise + toolchains -------------------------------------------------------
section "mise"
export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:$PATH"
HAS_MISE_CONFIG=0
MISE_TRUSTED=0
[ -f mise.toml ] || [ -f .mise.toml ] || [ -f .config/mise/config.toml ] && HAS_MISE_CONFIG=1
if command -v mise >/dev/null 2>&1; then
  ok "mise $(mise --version 2>/dev/null | head -1)"
  if [ "$HAS_MISE_CONFIG" = 1 ]; then
    if mise ls >/dev/null 2>&1 && ! mise ls 2>&1 >/dev/null | grep -qi "not trusted"; then
      MISE_TRUSTED=1
      ok "config trusted"
    elif [ "$FIX" = 1 ] && mise trust; then
      MISE_TRUSTED=1
      ok "trusted mise config"
    else
      warn "mise config not trusted — fix: mise trust"
    fi
    # An untrusted config makes mise silently ignore mise.toml, so toolchain
    # status can only be judged once trusted.
    if [ "$MISE_TRUSTED" = 1 ]; then
      missing="$(mise ls --missing 2>/dev/null || true)"
      if [ -n "$missing" ]; then
        if [ "$FIX" = 1 ]; then
          mise install && ok "installed missing toolchains" || bad "mise install failed — run manually to see why"
        else
          bad "missing toolchains: $(echo "$missing" | awk '{print $1, $2}' | tr '\n' ' ')— fix: mise install"
        fi
      else
        ok "all toolchains from mise.toml installed"
      fi
    else
      warn "toolchain status unknown until the config is trusted"
    fi
  else
    warn "no mise.toml in project — pin toolchains there ([tools]) so containers and cloud sessions match"
  fi
else
  bad "mise not installed — fix: curl https://mise.run | sh (or rebuild the container)"
fi

# --- volume ownership --------------------------------------------------------
if [ "$MODE" = devcontainer ]; then
  section "volume ownership"
  . "$SCRIPT_DIR/owned-paths.sh"
  bad_own=""
  for d in $DEV_OWNED_PATHS; do
    [ -e "$d" ] || continue
    [ -O "$d" ] || bad_own="$bad_own $d"
  done
  if [ -n "$bad_own" ]; then
    if [ "$FIX" = 1 ]; then
      sudo chown -R "$(id -un)":"$(id -gn)" $bad_own && ok "reclaimed ownership of:$bad_own"
    else
      bad "not owned by $(id -un):$bad_own — fix: --fix (sudo chown)"
    fi
  else
    ok "volumes owned by $(id -un)"
  fi
fi

# --- project -----------------------------------------------------------------
section "project"
if [ "$HAS_MISE_CONFIG" = 1 ] && [ "$MISE_TRUSTED" = 0 ]; then
  warn "cannot inspect mise tasks until the config is trusted (mise trust)"
elif command -v mise >/dev/null 2>&1 && mise tasks info setup >/dev/null 2>&1; then
  ok "'mise run setup' available for dependency install"
else
  warn "no 'setup' task in mise.toml — add one so bootstrap/cloud sessions can install dependencies"
fi
if [ -f .pre-commit-config.yaml ]; then
  hook_path="$(git rev-parse --git-path hooks/pre-commit 2>/dev/null || echo .git/hooks/pre-commit)"
  if [ -f "$hook_path" ]; then
    ok "pre-commit hooks installed"
  else
    warn "pre-commit config present but hooks not installed — fix: run your hook installer (e.g. 'prek install' or 'pre-commit install')"
  fi
fi
if command -v curl >/dev/null 2>&1; then
  # Any HTTP response (even 4xx) proves reachability — no -f here.
  if curl -sSI --max-time 5 -o /dev/null https://api.anthropic.com 2>/dev/null; then
    ok "network: api.anthropic.com reachable"
  else
    warn "cannot reach api.anthropic.com (offline, proxy, or firewall?)"
  fi
fi

# --- summary -----------------------------------------------------------------
printf '\ndoctor: %d ok, %d warnings, %d problems' "$PASS" "$WARN" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf ' — run with --fix to repair, or apply the fix commands above\n'
  exit 1
fi
printf '\n'

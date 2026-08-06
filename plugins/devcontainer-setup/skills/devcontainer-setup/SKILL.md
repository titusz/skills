---
name: devcontainer-setup
description: >-
  Generate or upgrade a complete .devcontainer setup: host git, Claude Code, and Codex
  credentials mounted in, toolchains pinned via mise, a doctor check/repair command, Anthropic
  cloud bootstrap, and zero secrets in committed files. Cross-platform (Windows/macOS/Linux
  hosts), editor-agnostic (Zed, VS Code, devcontainer CLI). Not for production Dockerfiles,
  docker-compose services, or CI images.
disable-model-invocation: true
argument-hint: '[target-dir] [project brief]'
---

# Devcontainer Setup

Generate a `.devcontainer/` configuration that gives every developer (and coding agent) a
ready-to-work container: host git identity and GitHub auth wired in, Claude Code and Codex signed
in via host credential mounts, toolchains pinned and installed through mise, and a `doctor`
command that verifies or repairs the whole setup. The same repo also bootstraps correctly in
Anthropic cloud sessions, which ignore `.devcontainer/` entirely.

All template files live in `assets/` and are proven patterns; copy them rather than writing
config from scratch, and adapt only the marked project-specific parts.

## Input

Invocation arguments (empty when none were passed):

$ARGUMENTS

The first argument names the target project directory when it is a path; everything else is a
free-text project brief — name, languages, tools, GPU needs, ports. The brief is
authoritative: it overrides whatever inspection would infer, and in a fresh or empty project
it may be the only source of truth.

## Generated layout

| File                               | Role                                                                        |
| ---------------------------------- | --------------------------------------------------------------------------- |
| `.devcontainer/devcontainer.json`  | Mounts, env, lifecycle commands (from `assets/devcontainer.json`)           |
| `.devcontainer/Dockerfile`         | Generic image: base tools, gh, mise, agent CLIs (from `assets/Dockerfile`)  |
| `.devcontainer/init-host.sh`       | Host pre-flight: create stubs so mounts never fail                          |
| `.devcontainer/post-create.sh`     | In-container setup orchestrator                                             |
| `.devcontainer/bootstrap.sh`       | Shared toolchain/deps install (devcontainer + Anthropic cloud)              |
| `.devcontainer/setup-gitconfig.sh` | Container gitconfig: host include + gh credential helper                    |
| `.devcontainer/setup-claude.sh`    | Merge Claude sign-in state from read-only host mount                        |
| `.devcontainer/setup-codex.sh`     | Seed Codex volume from read-only host mount                                 |
| `.devcontainer/owned-paths.sh`     | Single list of dev-owned paths (sourced by post-create + doctor)            |
| `.devcontainer/doctor.sh`          | Check/repair everything (`--fix`)                                           |
| `mise.toml`                        | Toolchain pins (`[tools]`) + `setup`/`doctor` tasks                         |
| `.claude/settings.json`            | `SessionStart` hook for Anthropic cloud bootstrap (merged, not overwritten) |

## Workflow

### 1. Inspect the target project

Determine, in the project root (the target-dir argument, or the current directory):

- **Project name**: the directory/repo name, kebab-case. Used for the container name, volume
    name prefixes, and the `/workspace/<name>` path.
- **Existing setup**: if `.devcontainer/` already exists, switch to upgrade mode (step 6).
- **Languages and package managers**: look for `pyproject.toml`/`uv.lock`, `package.json`,
    `go.mod`, `Cargo.toml`, `Gemfile`, `*.csproj`, etc.
- **Existing mise.toml**: reuse its `[tools]` and tasks; never discard user pins.
- **System library needs**: dependencies that require apt packages (e.g. audio/video → `ffmpeg`,
    postgres client libs → `libpq-dev`). See `references/languages.md`.
- **GPU needs**: ML dependencies (`torch`, `tensorflow`, `jax`, `cupy`, `onnxruntime-gpu`) →
    apply the CUDA recipe in `references/gpu-cuda.md` (commit-safe GPU access via
    `hostRequirements`, degrades to CPU-only on hosts without a GPU).
- **Fresh or empty project** (no manifests, lockfiles, or source to inspect): take the
    project name and stack entirely from the project brief; when the brief doesn't answer a
    needed question either, ask the user instead of guessing defaults.

### 2. Copy and adapt the templates

Copy every file from `assets/` except `mise.toml` into `.devcontainer/`. Place `mise.toml` at
the project root if none exists; when one already exists, merge the `[tasks.setup]` and
`[tasks.doctor]` blocks from the template into it, preserving all existing tools and tasks
(both tasks are load-bearing: `bootstrap.sh` runs `setup`, and the hand-off promises
`mise run doctor`). Then:

1. Replace every `{{PROJECT_NAME}}` placeholder (in `devcontainer.json`, `Dockerfile`,
    `mise.toml`) with the project name.
2. Tailor per language using `references/languages.md`: add cache-volume mounts and
    `containerEnv` entries to `devcontainer.json`, fill `[tools]` and the `setup` task in
    `mise.toml`, and add apt packages only under the `PROJECT-APT` marker in the Dockerfile.
3. Keep the Dockerfile generic otherwise — language toolchains come from `mise install` at
    postCreate, never from the Dockerfile.

### 3. Wire the Anthropic cloud bootstrap

Anthropic cloud sessions (claude.ai/code) do not read `.devcontainer/`. Merge a `SessionStart`
hook into the project's `.claude/settings.json` (create the file if missing, preserve existing
keys — never overwrite):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "sh -c 'if [ \"$CLAUDE_CODE_REMOTE\" = \"true\" ]; then bash .devcontainer/bootstrap.sh; fi'",
            "timeout": 600
          }
        ]
      }
    ]
  }
}
```

The `CLAUDE_CODE_REMOTE` guard makes the hook a no-op in local sessions. The hook alone
re-runs the full toolchain install every cloud session (it fires after the environment
snapshot is cached — 1–5 min each time), so whenever the user works on claude.ai/code
regularly, also hand them the one-line setup-script snippet from
`references/customization.md`, which moves the install into the cached snapshot and turns
the hook into a fast no-op.

### 4. Guard line endings

Generated shell scripts run inside Linux; CRLF breaks them. Append to the project's
`.gitattributes` (create if missing):

```
.devcontainer/*.sh text eol=lf
```

Write all generated files with LF endings.

### 5. Leak check (mandatory)

The generated files land in public repositories. Before finishing, grep every generated file
and confirm none contains:

- Absolute host paths or usernames (`C:\Users\...`, `/Users/...`, `/home/<name>`)
- Email addresses, tokens, API keys, or anything from the user's environment
- Host-specific mounts that only exist on this machine (extra data/reference mounts belong in
    opt-in extras — see `references/customization.md` — that the user must add consciously)

Host specifics may only enter at runtime via `${localEnv:...}` expansion.

### 6. Upgrade mode

When `.devcontainer/` already exists, do not regenerate blindly:

1. Read the existing files and list project-specific customizations: extra mounts, ports,
    `runArgs` (GPU, memory), apt packages, env vars, lifecycle extras.
2. Diff against the current templates and apply the pattern piecewise — the checklist and
    rationale for each element is in `references/design.md` (§ Upgrade checklist).
3. Preserve every customization; carry it into the marked sections of the new files.
4. Show the user a summary of what changed and why before writing.

### 7. Verify and hand off

- Validate `devcontainer.json` is valid JSON and every script referenced by its lifecycle
    commands exists.
- Run `bash -n` on every generated `.sh` file.
- Tell the user the first-run steps: reopen in container (Zed/VS Code/`devcontainer up`), watch
    `post-create.sh` finish with the doctor report, then `mise run doctor` any time (or
    `bash .devcontainer/doctor.sh --fix` to repair).
- Mention graceful degradation: hosts without Claude/Codex/git setup still start — the doctor
    explains how to sign in from inside the container. Claude sign-ins land on the host
    `~/.claude` mount; Codex logins and git identity persist in named volumes across rebuilds.

## Key invariants (do not break)

- **Home resolution**: mounts use `${localEnv:HOME}${localEnv:USERPROFILE}` concatenation — the
    cross-platform idiom. Never use only one. Caveat: a Windows setup that defines `HOME`
    globally expands both and breaks every mount path; `init-host.sh` detects and warns about
    this (registry probe).
- **Claude state via `CLAUDE_CONFIG_DIR=/home/dev/.claude` + host seed**: never rw-bind-mount
    the single file `~/.claude.json` — Claude Code replaces it by atomic rename, which a file
    mountpoint cannot track (stale reads on host saves, EBUSY on container saves). The env var
    keeps the container's `.claude.json` inside the mounted directory instead, where renames
    work and state survives rebuilds. But sign-in/account state (`oauthAccount`) and the
    onboarding flag live in `.claude.json`, not `.credentials.json` — so the host file is
    additionally mounted read-only at `~/.claude.json-host` and `setup-claude.sh` merges
    exactly those two fields into the container copy when it lacks either (never a whole-file
    copy, which would import host-only MCP servers and history). Dropping the seed brings
    back a login prompt on first create.
- **Codex on a volume**: `~/.codex` must stay a named volume seeded from the read-only
    `~/.codex-host` bind mount. Codex's SQLite/WAL storage corrupts on Windows bind mounts
    (`disk I/O error`). Full story in `references/design.md`.
- **Scripts run via `bash script.sh`**: Windows bind mounts cannot preserve exec bits.
- **Non-fatal setup**: credential seeding must never fail container creation.
- **mise is the single source of truth** for tool versions; the Dockerfile stays generic.
- **Agent CLIs**: installed together via npm at latest, verified at build.
- **No secrets, no personal paths** in any committed file.

## Additional resources

- **`references/languages.md`** — per-language tailoring: mise `[tools]`, `setup` task, cache
    volumes, `containerEnv`, apt packages, doctor notes.
- **`references/gpu-cuda.md`** — CUDA GPU support for ML projects: `hostRequirements.gpu`,
    host prerequisites per OS, shared-memory sizing, toolkit escape hatch, model cache.
- **`references/customization.md`** — opt-in extras: GPU, ports, memory limits, extra read-only
    reference mounts, network firewall, Anthropic cloud setup-script snippet, org policy.
- **`references/design.md`** — rationale for every element, degradation matrix, upgrade
    checklist, and the security model. Read before deviating from the templates.

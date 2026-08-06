# Design rationale

Why each element of the template exists, what breaks without it, and how to upgrade older
setups. Read this before deviating from the templates or when debugging a generated setup.

## Mount model

| Mount                                                                      | Type         | Why                                                                                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.claude` → `/home/dev/.claude`                                          | bind, rw     | Claude Code config + OAuth credentials. Read-write so token refreshes and in-container sign-ins write back to the host — the host and container share one session that survives rebuilds. `containerEnv` sets `CLAUDE_CONFIG_DIR=/home/dev/.claude`, so the container's `.claude.json` also lives here (see below).         |
| `~/.claude.json` → `/home/dev/.claude.json-host`                           | bind, **ro** | Seed source only. Sign-in/account state (`oauthAccount`) and the onboarding flag live in this file, not in `.credentials.json`; `setup-claude.sh` merges those two fields into `$CLAUDE_CONFIG_DIR/.claude.json` when the container copy lacks either, so the host sign-in carries over without a login prompt (see below). |
| `~/.codex` → `/home/dev/.codex-host`                                       | bind, **ro** | Seed source only. See "Codex and SQLite/WAL".                                                                                                                                                                                                                                                                               |
| volume → `/home/dev/.codex`                                                | volume       | Codex's live home.                                                                                                                                                                                                                                                                                                          |
| `~/.gitconfig` → `/home/dev/.gitconfig-host`                               | bind, ro     | Host git identity/aliases, inherited via `[include]` from a generated container `~/.gitconfig` that overrides credential helpers (host helpers reference binaries that don't exist in the container).                                                                                                                       |
| volume → `/commandhistory`, `~/.cache`, `~/.config`, `~/.local/share/mise` | volume       | Shell history, download caches, tool logins (`gh auth login` → `~/.config/gh`), and mise toolchains survive rebuilds. Named per-project + `${devcontainerId}` so parallel projects never collide.                                                                                                                           |

### Why `.claude.json` is seeded, not rw-bind-mounted

Claude Code saves `~/.claude.json` via atomic temp-file+rename (several times a minute in an
active session). A rw single-file bind mount pins one inode, so a host-side save orphans the
container's view (stale reads forever), and an in-container rename over the mountpoint fails
with EBUSY on every Docker backend. And the "shared project state" it promised was illusory
anyway: project entries are keyed by absolute path, and `/workspace/...` never matches
`C:\...`. Instead, `containerEnv` sets `CLAUDE_CONFIG_DIR=/home/dev/.claude`: the container's
`.claude.json` lives *inside* the mounted `~/.claude` directory, where renames are ordinary
file operations — so saves work and container state still survives rebuilds on the host
mount. Host and container keep separate `.claude.json` files; credentials stay shared.

The catch: sign-in/account state (`oauthAccount`, onboarding flags) lives in `.claude.json`,
not in `.credentials.json` — a fresh container with only the credentials mount still prompts
for login. Hence the read-only `~/.claude.json-host` mount plus `setup-claude.sh` (run by
`post-create.sh`, re-runnable via `doctor.sh --fix`): when the host file has an
`oauthAccount` object *and* `hasCompletedOnboarding: true` but the container's `.claude.json`
lacks either, exactly those two fields are merged into the container copy. Never a whole-file
copy: the host file also carries stdio MCP servers with host paths, `installMethod`, and the
full `projects`/history map — none of which can work in the container. The merge preserves
everything the container has accumulated (trust dialogs, MCP servers), Claude never writes to
the mountpoint (no EBUSY), and a completed in-container sign-in already has both fields, so
it is never touched again.

The read-only `~/.claude.json-host` view shares the inode-pinning caveat: after a host-side
save (atomic rename), backends that pin the original inode keep serving the create-time
snapshot. The mount is therefore trustworthy only at first create — which is the only moment
anything reads it. A sign-in completed on the host *after* creation reaches the container
only via a rebuild; re-running `setup-claude.sh` against the stale mount finds no sign-in
state and reports that instead of seeding.

### Home resolution across platforms

`${localEnv:HOME}${localEnv:USERPROFILE}` concatenates two variables of which exactly one is
normally set in the editor/CLI process environment: `HOME` on Linux/macOS, `USERPROFILE` on
Windows. This is the standard cross-platform devcontainer idiom. Known caveat: a Windows
setup that defines `HOME` globally (some Cygwin/MSYS/gpg workflows) expands both into a
broken concatenation — the fix is removing the global `HOME` variable, not editing the
template. `init-host.sh` probes the Windows registry for a global `HOME` and warns before
the container builds.

### Codex and SQLite/WAL (do not "simplify" to a plain bind mount)

Codex keeps state in SQLite databases opened in WAL mode under `~/.codex`. WAL requires a
shared-memory file accessed via mmap + POSIX locks, which Docker Desktop's Windows file sharing
(gRPC-FUSE/virtiofs) does not support → `disk I/O error` (SQLITE_IOERR_SHMOPEN). A shared bind
mount also lets host and container Codex builds collide on migration checksums. Hence:
volume for the live `~/.codex`, read-only host mount for seeding auth/config on first create,
seed-only-if-volume-empty so a refreshed container token is never clobbered by a staler host
copy. Claude Code has no SQLite store, so its rw bind mount is safe — and preferable, because
OAuth token refreshes stay in sync with the host.

## Degradation matrix

Startup must succeed on a host that has none of the tooling configured:

| Missing on host                                           | What happens                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.claude`, `~/.claude.json`, `~/.codex`, `~/.gitconfig` | `init-host.sh` creates empty stubs before build; mounts succeed; container starts signed-out.                                                                                                                                                                                                                                                                                                                                |
| Claude credentials                                        | Container works; doctor says: run `claude` to sign in. The sign-in lands on the host mount → survives rebuilds and pre-authorizes a later host install. macOS hosts always take this path even when signed in: Claude Code stores OAuth tokens in the Keychain there, not in `~/.claude/.credentials.json`, so host sessions cannot carry over.                                                                              |
| Codex credentials                                         | Same, via `codex login --device-auth`; stored in the volume.                                                                                                                                                                                                                                                                                                                                                                 |
| git identity                                              | Include of empty `~/.gitconfig-host` is harmless; doctor prints the exact fix commands, targeting `~/.config/git/config` (volume-backed, included last by the generated config) so the identity survives rebuilds.                                                                                                                                                                                                           |
| `GH_TOKEN`                                                | `containerEnv` passes an empty string; `gh auth login` in the container persists in the `~/.config` volume.                                                                                                                                                                                                                                                                                                                  |
| NVIDIA GPU / container runtime (GPU-enabled projects)     | `hostRequirements.gpu: "optional"` makes launchers skip the `--gpus` flag; the container starts CPU-only and the doctor's GPU section names what the host is missing. See `references/gpu-cuda.md`.                                                                                                                                                                                                                          |
| bash on a Windows host                                    | Hard requirement (Git Bash or WSL): `initializeCommand` needs *some* bash. Default Git-for-Windows installs put only `Git\cmd` on PATH, so an unqualified `bash` often resolves to the System32 WSL launcher — `init-host.sh` detects WSL and re-targets the real Windows home via `cmd.exe`/`wslpath`. With neither Git Bash on PATH nor a WSL distro, container creation fails before build with "bash is not recognized". |

Non-fatality rules that make this work: `setup-claude.sh` and `setup-codex.sh` always exit 0;
`post-create.sh` treats credential seeding as advisory; `doctor.sh` reports instead of failing creation (it is
informational in postCreate, strict only when run manually). `bootstrap.sh` is deliberately
*not* on this list: a failed toolchain/dependency install makes `post-create.sh` exit nonzero
(after the doctor has reported details), because a container without toolchains is not ready.

## Anthropic cloud (claude.ai/code)

Cloud sessions run in Anthropic's sandbox and **ignore `.devcontainer/` entirely** — no
Dockerfile build, no mounts, no postCreate. What carries over is the repo itself, which is why
the bootstrap path is split out:

- `bootstrap.sh` contains everything both worlds need (ensure mise → `mise trust` →
    `mise install` → `mise run setup`) and nothing container-specific.
- Locally, `post-create.sh` calls it after the credential/gitconfig steps.
- In the cloud, the `SessionStart` hook in `.claude/settings.json` calls it, guarded by
    `CLAUDE_CODE_REMOTE=true` so local sessions (including on plain hosts) skip it. The hook has
    `timeout: 600` because first-run toolchain installs exceed the default hook timeout.
- SessionStart runs *after* the cloud's environment-caching snapshot, so per-session installs
    repeat; the setup-script snippet in `customization.md` moves them into the cached snapshot.

Git identity, GitHub auth, and Claude credentials are provided by the cloud platform itself —
none of the devcontainer credential plumbing applies there, which is why `doctor.sh` gates its
GitHub-auth, credential-mount, Codex, and volume-ownership sections on devcontainer mode; the
generic git, mise, and project checks still run everywhere.

## Security model (public-repo safe)

- **Nothing secret is committed**: host specifics enter only at runtime through
    `${localEnv:...}` expansion (which resolves on the *user's* machine) and bind mounts.
- **No SSH keys or host credential stores are mounted.** GitHub auth flows exclusively through
    `gh auth git-credential` — fed by `GH_TOKEN` passthrough or an in-container `gh auth login`.
- **Commit signing is disabled in the container** via `GIT_CONFIG_*` env (signing keys stay on
    the host); host commits remain signed.
- The leak check in SKILL.md step 5 is mandatory because upgrades often start from configs
    containing personal reference mounts (`E:/data`, `~/Code/...`) — those must never be copied
    into a template for others.

## Editor compatibility

Only spec-standard properties are used — no `customizations.vscode`, no feature that ties the
config to one editor. Verified consumers: Zed (agent servers + dev containers), VS Code Dev
Containers, the `devcontainer` CLI (`devcontainer up --workspace-folder .`), JetBrains.
GitHub Codespaces limitation: host bind mounts don't exist there; Codespaces users should rely
on the cloud-style bootstrap (Codespaces secrets + `SessionStart`) rather than this mount model.

## Upgrade checklist

For projects with an older devcontainer (pre-dating this pattern), check each element and port
what's missing, preserving all project-specific customizations:

1. **Home concat**: mounts still `${localEnv:USERPROFILE}`-only (Windows-only)? → switch to the
    concat idiom.
2. **Codex**: `~/.codex` still a rw bind mount? → volume + ro `~/.codex-host` seed +
    `setup-codex.sh`.
3. **mise**: toolchains baked in the Dockerfile? → move version pins to `mise.toml [tools]`,
    strip the Dockerfile to the generic template (keep apt system libs under `PROJECT-APT`),
    add the `~/.local/share/mise` volume, `mise activate` lines, and shims PATH entry.
4. **Version-pinned agent CLIs** (`CLAUDE_CODE_VERSION` build arg)? → plain
    `@latest` npm install of both CLIs.
5. **postCreate as a long `&&` one-liner in devcontainer.json?** → move into
    `post-create.sh` + `bootstrap.sh` (cloud reuse).
6. **No doctor?** → add `doctor.sh` + the `doctor` mise task; extend `DEV_OWNED_PATHS` in
    `owned-paths.sh` with any project-specific volumes (venv, cargo, go).
7. **`~/.claude.json` still rw-bind-mounted?** → replace with the read-only
    `~/.claude.json-host` seed mount + `setup-claude.sh` (called from post-create), and set
    `containerEnv.CLAUDE_CONFIG_DIR=/home/dev/.claude` (rw single-file mounts break Claude
    Code's atomic saves; no seed at all brings back the first-run login prompt — see the
    mount model above).
8. **No cloud path?** → add `bootstrap.sh` + the guarded `SessionStart` hook.
9. **`~/.config` and `~/.cache` volumes missing?** → add (gh logins and caches currently die
    on rebuild).
10. **Leak check** the result — older configs frequently embed machine-specific mounts.
11. Keep proven extras exactly as found — port publishing, memory limits, reference mounts,
    plugin-path fixups — with one exception: a committed `"runArgs": ["--gpus", "all"]` breaks
    container creation on GPU-less hosts; convert it to
    `"hostRequirements": { "gpu": "optional" }` (see `references/gpu-cuda.md`).

## Known sharp edges

- **Exec bits**: Windows bind mounts can't preserve them — that is why every script call is
    `bash path/to/script.sh`. Never change lifecycle commands to `./script.sh`.
- **CRLF**: a checkout with `core.autocrlf=true` turns the scripts into CRLF and they fail in
    Linux with cryptic `$'\r': command not found` — hence the `.gitattributes` rule and the
    doctor's line-ending check.
- **Plugin marketplace paths**: the host Claude install writes absolute Windows paths into
    `~/.claude/plugins/known_marketplaces.json`; the shared rw mount exposes them to the
    container where plugins then fail to resolve. `doctor.sh --fix` rewrites them (the host
    rewrites them back — harmless ping-pong).
- **TOML top-level keys**: when editing `~/.codex/config.toml`, new top-level keys must be
    *prepended* — appended keys land inside the last `[table]` and are silently misread
    (`setup-codex.sh` handles this).
- **Stale Codex tokens**: the `~/.codex` volume is seeded only when empty, so a token that
    expires in the container is never refreshed from a newer host login. Recovery: run
    `codex login --device-auth` inside the container (overwrites the volume copy). The doctor's
    "credentials present" only means the file exists — it cannot detect staleness.
- **Seeded `config.toml` may carry host-only settings**: the wholesale first-create seed can
    import absolute host paths (stdio MCP server commands, notify hooks) that cannot run in the
    container. Edit the volume copy at `~/.codex/config.toml` — it is never re-seeded.
- **JSON only**: keep `devcontainer.json` comment-free strict JSON so non-JSONC tooling and
    this repo's validators can parse it.

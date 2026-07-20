# Per-language tailoring

The Dockerfile stays generic; every language lands through three project files:

1. `mise.toml` — `[tools]` pins the toolchain, `[tasks.setup]` installs dependencies.
2. `devcontainer.json` — named cache volumes (so rebuilds don't re-download the world) and
    `containerEnv` entries.
3. `Dockerfile` — apt packages under the `PROJECT-APT` marker, only when a dependency needs
    system libraries.

Volume naming convention: `{{PROJECT_NAME}}-<what>-${devcontainerId}` mounted at the cache's
canonical path. The generic template already persists `~/.cache` (which covers uv, pip, and most
XDG-compliant tools) and `~/.local/share/mise` (the toolchains themselves).

Detect languages from lockfiles/manifests, not file extensions. Multi-language projects combine
sections; the `setup` task chains installs with `&&`.

## Python (uv)

Detect: `pyproject.toml`, `uv.lock`.

```toml
[tools]
python = "3.13" # match requires-python / .python-version
uv = "latest"

[tasks.setup]
run = "uv sync"
```

devcontainer.json — keep the venv out of the bind-mounted workspace for filesystem speed:

```json
"source={{PROJECT_NAME}}-venv-${devcontainerId},target=/home/dev/.venvs/{{PROJECT_NAME}},type=volume"
```

```json
"UV_PROJECT_ENVIRONMENT": "/home/dev/.venvs/{{PROJECT_NAME}}"
```

Add the venv path to `DEV_OWNED_PATHS` in `.devcontainer/owned-paths.sh` — the volume mount
point is not pre-created in the Dockerfile, so Docker creates it root-owned on first create
and `uv sync` fails with EACCES until post-create (or `doctor --fix`) repairs it. The uv
download cache is already covered by the `~/.cache` volume. If the project uses
pre-commit/prek, extend the setup task: `uv sync && uv run prek install` (or
`pre-commit install`).

### ML / CUDA projects

When dependencies include `torch`, `tensorflow`, `jax`, `cupy`, or `onnxruntime-gpu`, also
apply `references/gpu-cuda.md`: `hostRequirements.gpu: "optional"` (commit-safe GPU access
that degrades to CPU), `--shm-size` for DataLoader workers, and — only for kernel-compiling
dependencies — the CUDA toolkit escape hatch. Wheel-based ML needs no Dockerfile changes.

## Node / TypeScript

Detect: `package.json` (+ lockfile → pick the right install command).

```toml
[tools]
node = "24" # match engines/.nvmrc; omit to use the image's node

[tasks.setup]
run = "npm ci" # or: pnpm install --frozen-lockfile / yarn install --immutable
```

`node_modules` lives in the workspace bind mount — acceptable for most projects. Unlike the
Python venv it cannot be relocated outside the project tree (only shadow-mounted), which is
why the two recipes differ. For very large installs, mount a volume at
`/workspace/{{PROJECT_NAME}}/node_modules` and add it to `DEV_OWNED_PATHS` in
`.devcontainer/owned-paths.sh`, since it sits inside the workspace.

npm caches at `~/.npm` and pnpm's store at `~/.local/share/pnpm` — neither inside the
persisted `~/.cache` — so redirect them onto the cache volume or rebuilds re-download every
dependency. In `containerEnv`:

```json
"npm_config_cache": "/home/dev/.cache/npm",
"npm_config_store_dir": "/home/dev/.cache/pnpm-store"
```

(`npm_config_store_dir` is read by pnpm; npm ignores it.)

## Go

Detect: `go.mod`.

```toml
[tools]
go = "1.26" # match the go.mod directive

[tasks.setup]
run = "go mod download"
```

devcontainer.json:

```json
"source={{PROJECT_NAME}}-go-mod-${devcontainerId},target=/home/dev/go/pkg/mod,type=volume"
```

The build cache defaults to `~/.cache/go-build` — already persisted. Add `/home/dev/go/pkg/mod`
to `DEV_OWNED_PATHS` in `.devcontainer/owned-paths.sh`. If the project doesn't need cgo, set
`"CGO_ENABLED": "0"` in `containerEnv` (the base image has a C toolchain either way).

## Rust

Detect: `Cargo.toml`.

```toml
[tools]
rust = "1.89" # match rust-toolchain.toml if present

[tasks.setup]
run = "cargo fetch"
```

devcontainer.json:

```json
"source={{PROJECT_NAME}}-cargo-registry-${devcontainerId},target=/home/dev/.cargo/registry,type=volume",
"source={{PROJECT_NAME}}-cargo-git-${devcontainerId},target=/home/dev/.cargo/git,type=volume"
```

Add both paths to `DEV_OWNED_PATHS` in `.devcontainer/owned-paths.sh`. Crates with C
dependencies often need `libssl-dev` under
`PROJECT-APT` (`build-essential`/`pkg-config` are already in the base list).

## Other stacks

The same recipe applies to anything mise supports (`mise registry` lists hundreds): pin in
`[tools]`, install deps in `[tasks.setup]`, persist the stack's cache directory as a named
volume if it lives outside `~/.cache`, and put system libraries under `PROJECT-APT`. Examples:

- **Java**: `java = "temurin-21"`, `maven`/`gradle` in tools; volume for `~/.m2` or
    `~/.gradle`.
- **Ruby**: `ruby = "3.4"`; `bundle install` as setup; `libyaml-dev` apt package.
- **.NET**: `dotnet = "9"`; volume for `~/.nuget`.

When a toolchain is not available (or too slow to install) via mise — CUDA, heavyweight SDKs —
fall back to installing it in the Dockerfile below the `PROJECT-APT` marker and say so in a
comment; that is the deliberate escape hatch from the mise-first rule.

## System libraries (PROJECT-APT)

Common triggers spotted in dependencies:

| Dependency signal                      | apt packages                                                    |
| -------------------------------------- | --------------------------------------------------------------- |
| audio (soundfile, librosa, torchaudio) | `ffmpeg libsndfile1`                                            |
| images (Pillow with uncommon formats)  | `libjpeg-dev libpng-dev`                                        |
| psycopg / pg native drivers            | `libpq-dev`                                                     |
| mysqlclient                            | `default-libmysqlclient-dev`                                    |
| lxml                                   | `libxml2-dev libxslt1-dev`                                      |
| ssl-linked crates/gems                 | `libssl-dev`                                                    |
| headless browsers (playwright)         | prefer the tool's own `--with-deps` installer in the Dockerfile |

## Doctor implications

`doctor.sh` needs no per-language edits: it validates `mise ls --missing` (toolchains) and the
presence of a `setup` task generically. When adding extra named volumes (go mod, cargo, ...),
append their container paths to `DEV_OWNED_PATHS` in `.devcontainer/owned-paths.sh` — both
`post-create.sh` and doctor's `volume ownership` section source that one list, so `--fix`
repairs them automatically.

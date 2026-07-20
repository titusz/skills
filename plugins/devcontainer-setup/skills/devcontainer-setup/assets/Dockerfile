# Devcontainer image for {{PROJECT_NAME}}.
#
# Deliberately generic: language toolchains are NOT baked in here — they are
# provisioned at postCreate by `mise install` from the project's mise.toml
# (single source of truth for versions) and persisted in a named volume, so
# this Dockerfile stays nearly identical across projects. Only OS-level
# packages (apt) belong in this file. Host- and project-specific layers sit
# at the END so everything above them stays byte-identical across projects
# and shares the Docker build cache.
#
# The node base image provides npm for the agent CLIs (Claude Code, Codex);
# projects that pin their own node version via mise shadow it through shims.
FROM node:24-bookworm

# Base system packages: shell conveniences, dev CLIs, and a C toolchain
# (build-essential) so mise-built runtimes and native extensions compile.
# PROJECT-APT: add project-specific system libraries to this list
# (e.g. ffmpeg, libsndfile1, libpq-dev) — keep language runtimes out.
RUN apt-get update && apt-get install -y --no-install-recommends \
    less procps sudo fzf zsh man-db unzip gnupg2 jq nano vim ca-certificates \
    build-essential pkg-config \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# GitHub CLI — backs the container-local git credential helper (see
# setup-gitconfig.sh) so no SSH keys or host credential stores are mounted.
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user with passwordless sudo (required: Claude Code refuses
# --dangerously-skip-permissions as root, and volumes need chown at
# postCreate). The base image's node user already holds UID/GID 1000, so
# rename it instead of adding a second user — dev must own UID 1000 for the
# Dev Containers UID remap (updateRemoteUserUID) to work on Linux hosts.
RUN usermod --login dev --home /home/dev --move-home --shell /bin/zsh node \
    && groupmod --new-name dev node \
    && usermod -aG sudo dev \
    && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && chmod 0440 /etc/sudoers.d/dev

# Shell history persists across rebuilds via a named volume mounted here
RUN mkdir /commandhistory \
    && touch /commandhistory/.zsh_history \
    && chown -R dev /commandhistory

# Pre-create the workspace and the named-volume mount-points with dev
# ownership so first-use volumes inherit it. (Bind-mount targets need no
# stubs — Docker overlays them with the mounted source's metadata.)
RUN mkdir -p /workspace \
    /home/dev/.claude \
    /home/dev/.codex \
    /home/dev/.cache \
    /home/dev/.config \
    /home/dev/.local/share/mise \
    && chown -R dev:dev /workspace /home/dev

# Writable npm global prefix for the agent CLI installs below. Listed in
# owned-paths.sh: post-create re-chowns it when the Dev Containers UID remap
# moves dev off UID 1000 (the remap itself only chowns the home directory).
RUN mkdir -p /usr/local/share/npm-global \
    && chown -R dev:dev /usr/local/share/npm-global

ENV DEVCONTAINER=true

WORKDIR /workspace

# Switch to the non-root user for the remaining installs
USER dev
ENV HOME=/home/dev
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:/usr/local/share/npm-global/bin:$PATH"
ENV SHELL=/bin/zsh

# mise — tool version manager + task runner; toolchains land in the
# ~/.local/share/mise named volume at postCreate (`mise install`).
# Download-then-run so a failed download fails the build (a plain curl|sh
# succeeds silently on curl failure — /bin/sh has no pipefail).
RUN curl -fsSL https://mise.run -o /tmp/mise-install.sh \
    && sh /tmp/mise-install.sh \
    && rm /tmp/mise-install.sh

# Agent CLIs — installed the same way, always latest, verified at build so a
# broken install fails fast. Credentials come from host mounts at runtime,
# never from the image.
RUN npm install -g @anthropic-ai/claude-code@latest @openai/codex@latest \
    && claude --version \
    && codex --version

# ZSH with oh-my-zsh; history persists to the /commandhistory volume; mise is
# activated in both interactive shells
RUN curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -o /tmp/omz-install.sh \
    && sh /tmp/omz-install.sh --unattended \
    && rm /tmp/omz-install.sh \
    && echo 'export HISTFILE=/commandhistory/.zsh_history' >> $HOME/.zshrc \
    && echo 'eval "$(mise activate zsh)"' >> $HOME/.zshrc \
    && echo 'eval "$(mise activate bash)"' >> $HOME/.bashrc

# ---- host- and project-specific layers below: keep them last so the generic
# ---- layers above stay shared across projects in the build cache

ARG TZ
ENV TZ="$TZ"

# System-level git config survives setup-gitconfig.sh regenerating the user
# ~/.gitconfig on every container create
USER root
RUN git config --system --add safe.directory /workspace/{{PROJECT_NAME}}
USER dev

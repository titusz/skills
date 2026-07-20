# Paths that must stay owned by the dev user: named-volume mount points
# (created root-owned by some Docker backends) plus the shared npm prefix
# (left on the build-time UID when the Dev Containers UID remap moves dev).
# Sourced by post-create.sh and doctor.sh — extend this single list when
# adding project volumes (go mod, cargo, venv, ...); see references in
# the devcontainer-setup skill (languages.md, gpu-cuda.md).
DEV_OWNED_PATHS="/commandhistory $HOME/.cache $HOME/.config $HOME/.local/share/mise $HOME/.codex /usr/local/share/npm-global"

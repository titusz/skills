# Opt-in customizations

Everything here is deliberately absent from the default templates. Add only what the project
actually needs, and only into the marked/mount sections — the invariants in SKILL.md still
apply (no secrets, no host-specific paths that other contributors won't have).

## GPU access (CUDA)

```json
"hostRequirements": { "gpu": "optional" }
```

This alone gives ML projects CUDA in the container on GPU hosts while degrading to CPU-only
everywhere else — launchers inject `--gpus all` only when the NVIDIA runtime is detected. Never
commit `"runArgs": ["--gpus", "all"]` (fails container creation on GPU-less hosts). The full
recipe — host prerequisites per OS, why no CUDA toolkit is needed for wheel-based ML, the
`--shm-size` DataLoader trap, kernel-compilation escape hatch, shared model-cache volume — is in
`references/gpu-cuda.md`.

## Ports and resources

```json
"forwardPorts": [39123],
"runArgs": ["--memory=12g", "--memory-swap=14g"]
```

Prefer `forwardPorts` (editor-forwarded, works everywhere) over `-p` publishing in `runArgs`
unless something outside the editor must reach the port. Pick exotic dev-server ports to avoid
collisions across parallel projects.

## Extra read-only reference mounts

For sibling repos or datasets the agent should read but never modify:

```json
"source=${localEnv:HOME}${localEnv:USERPROFILE}/Code/sibling-repo,target=/reference/sibling-repo,type=bind,readonly"
```

These are inherently machine-specific: `init-host.sh` should warn (not fail) when the source is
missing, so add an advisory line there per mount, following its existing pattern:
`[ -e "$home/Code/sibling-repo" ] || echo "init-host: mount source missing: ..." >&2`. For fully portable references prefer a
shallow clone in `post-create.sh` instead:

```bash
[ -d reference/sibling-repo ] || git clone --depth 1 https://github.com/org/sibling-repo.git reference/sibling-repo
```

## Network egress firewall

To restrict outbound traffic to an allowlist (agent-safety hardening), adapt the
`init-firewall.sh` pattern from the official reference container
(github.com/anthropics/claude-code, `.devcontainer/`): it needs

```json
"runArgs": ["--cap-add=NET_ADMIN", "--cap-add=NET_RAW"]
```

plus a postCreate firewall script. Not included by default because the allowlist is
project-specific maintenance; without it, rely on the container boundary and permission modes.

## Anthropic cloud setup script (faster cloud startups)

The `SessionStart` hook makes cloud sessions work with zero configuration, but it runs *after*
environment caching, so heavy toolchain installs repeat each new session. To cache them,
paste this into the cloud environment's **Setup script** field (claude.ai/code → environment
settings):

```bash
bash .devcontainer/bootstrap.sh
```

The environment snapshot then already contains mise, the toolchains, and dependencies; the
SessionStart hook still runs but completes as a fast no-op. Re-save the environment (rebuilding
the cache) after changing `mise.toml` tool pins. Note that cloud environment variables and
setup scripts are visible to anyone who can edit the environment — no secrets there either.

## Organization policy inside the container

To enforce settings for every session in the container, bake managed settings into the image
(highest precedence in the settings hierarchy):

```dockerfile
RUN mkdir -p /etc/claude-code
COPY managed-settings.json /etc/claude-code/managed-settings.json
```

Useful keys: permission rules, `permissions.disableBypassPermissionsMode`, MCP allowlists.
Remember anyone with repo write access can edit this file; for non-bypassable policy use
server-managed settings instead.

## Telemetry / auto-update opt-outs

```json
"containerEnv": {
  "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
  "DISABLE_AUTOUPDATER": "1"
}
```

With the auto-updater disabled, new CLI versions arrive only via image rebuild — the
`@latest` install in the Dockerfile makes every rebuild pick them up.

## Unattended agents (`--dangerously-skip-permissions`)

The container already satisfies the CLI's requirement (non-root `remoteUser`). Before running
unattended, remember: the credentials on the host mounts (`~/.claude`, `~/.codex`) are readable
by anything the agent executes, and the workspace bind mount writes straight to the host repo.
Use only with trusted repositories; combine with the firewall above for meaningful containment.

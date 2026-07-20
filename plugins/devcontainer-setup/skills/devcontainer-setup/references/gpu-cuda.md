# CUDA GPU support

How to give ML projects CUDA acceleration in the container while keeping the committed config
safe for hosts without a GPU. Apply this recipe when the project depends on `torch`,
`tensorflow`, `jax[cuda...]`, `cupy`, `onnxruntime-gpu`, or similar — or when the user asks for
GPU support.

## The one safe way to request a GPU

Add to `devcontainer.json` (top level):

```json
"hostRequirements": { "gpu": "optional" }
```

Supporting launchers (VS Code Dev Containers, the reference `devcontainer` CLI — which Zed
delegates to via `devcontainer up`) probe Docker for the NVIDIA runtime and inject `--gpus all`
only when it is present. Hosts without a GPU start the same container CPU-only. That makes the
line safe to commit for every contributor and CI.

**Never commit `"runArgs": ["--gpus", "all"]`.** A hardcoded `--gpus` flag makes container
creation *fail* on any host without the NVIDIA runtime — the exact opposite of graceful
degradation. If a launcher turns out not to honor `hostRequirements.gpu` (older tooling), the
developer can add the flag locally without committing it.

Known edge case: detection checks for the NVIDIA *runtime* (`docker info` → `Runtimes.nvidia`),
not for an attached GPU. A machine with the toolkit installed but the GPU removed gets
`--gpus all` and fails to start; removing the toolkit (or the stale runtime registration)
resolves it.

## What the container needs: usually nothing

Modern ML wheels (PyTorch, JAX, TensorFlow) bundle their own CUDA runtime libraries; the NVIDIA
container runtime injects the driver libraries and `nvidia-smi` at container start. So for
wheel-based development the generic Dockerfile needs **no CUDA toolkit** — `uv sync` +
`hostRequirements` is the whole setup.

Only projects that *compile* CUDA kernels (flash-attn, custom `nvcc` extensions,
`torch.utils.cpp_extension`) need the toolkit. Escape hatch, under the `PROJECT-APT` marker:

```dockerfile
# PROJECT-APT: CUDA toolkit for compiling kernels (flash-attn etc.) — match the
# major version to the project's torch build
RUN curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb -o /tmp/cuda-keyring.deb \
    && dpkg -i /tmp/cuda-keyring.deb && rm /tmp/cuda-keyring.deb \
    && apt-get update && apt-get install -y --no-install-recommends cuda-toolkit-12-8 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

Swapping the base image for `nvidia/cuda:*-devel` is the last resort — it forfeits the generic
Dockerfile and needs node re-installed for the agent CLIs. Prefer the apt toolkit above.

## Shared memory (the classic PyTorch trap)

Docker's default `/dev/shm` is 64 MB; PyTorch `DataLoader` with `num_workers > 0` crashes with
cryptic bus errors. This flag needs no GPU and is safe on every host, so it *can* be committed:

```json
"runArgs": ["--shm-size=8g"]
```

## Host prerequisites (document in the project README)

- **Windows (Docker Desktop, WSL2 backend)**: only the Windows NVIDIA driver is required —
    `nvidia-smi` working in PowerShell is the whole test. Docker Desktop bundles the container
    toolkit. Never install a Linux GPU driver inside WSL.
- **Linux**: NVIDIA driver + `nvidia-container-toolkit` (registers the runtime the launcher
    detection looks for).
- **macOS**: no NVIDIA/CUDA — the container always runs CPU-only. That must stay a working mode.

Add a host-side advisory to `init-host.sh` (advisory pattern, never fail):

```bash
command -v nvidia-smi >/dev/null 2>&1 \
    || echo "init-host: no NVIDIA driver detected - container will run CPU-only" >&2
```

## Model cache across projects

The per-project `~/.cache` volume already persists Hugging Face downloads across rebuilds. For
multi-gigabyte models shared between projects, mount one *unscoped* volume over the HF subdir
(deliberately without the `${devcontainerId}` suffix, so every project reuses it):

```json
"source=hf-cache,target=/home/dev/.cache/huggingface,type=volume"
```

Add `$HOME/.cache/huggingface` to `DEV_OWNED_PATHS` in `.devcontainer/owned-paths.sh` (a nested
volume mount point is created root-owned).

## Doctor

The template `doctor.sh` already contains a GPU section that self-activates when
`devcontainer.json` requests a GPU — it reports the detected GPU by name, or explains why the
container is CPU-only with per-OS pointers. No per-project doctor edits are needed. GPU
passthrough is host-side, so there is nothing `--fix` can repair; the section warns instead of
failing because CPU-only is a supported degradation, not an error.

For a framework-level smoke test, extend the project's own tooling (not doctor.sh), e.g. a
`mise` task: `python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"`.

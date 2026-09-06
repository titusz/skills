---
name: generate-image
description: >-
  Generate or edit raster images (illustrations, photos, mockups, icons, textures, banners,
  sprites, concept art) with the Codex CLI's built-in image_gen tool, billed to the user's
  ChatGPT subscription — never an API key. Use whenever the user wants to create, draw,
  render, generate, edit, restyle, or iterate on an image, asks for "a picture of…",
  "an illustration for…", "make this image blue", "generate variants", or mentions
  reference images or applying an art style. Outputs land in the project's cauldron/images/
  folder with their prompt recorded. Do NOT use for SVG/vector work, diagrams better done
  in code, or when the user explicitly wants the OpenAI API or another image service.
user-invocable: true
argument-hint: <what to draw> [--edit <img>] [--ref <img>] [--style <name>] [--count N] [--fit WxH]
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion
---

# Generate Image

Turn a request into one or more raster images via Codex's built-in `image_gen` tool,
driven by the bundled script. The script owns every gotcha (stdin piping, API-key
stripping, read-only sandbox, harvesting by thread id), so never call `codex exec`
directly, never write API scripts, and never ask for an `OPENAI_API_KEY`.

## Tooling

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/codex_image.py" <command> ...
```

Abbreviated as `codex_image.py` below. If `${CLAUDE_PLUGIN_ROOT}` is unset, resolve the
path relative to this file (`../../scripts/codex_image.py`).

Commands:

| Command    | Purpose                                                                  |
| ---------- | ------------------------------------------------------------------------ |
| `doctor`   | Verify codex on PATH, ChatGPT auth, `image_generation` flag, no API keys |
| `generate` | Run one generation/edit; prints JSON with `outputs`, `sidecar`, `errors` |
| `fit`      | Resize/convert an existing image (`--fit WxH`, `--fit-mode`, `-o`)       |

`generate` options: `--prompt-file` (preferred) or `--prompt`, `--name <slug>`,
`--edit <img>` (repeatable, edit target), `--ref <img>` (repeatable, subject/composition
reference), `--style <card.md>`, `--count N`, `--fit WxH`, `--fit-mode cover|contain`,
`--format png|jpeg|webp`, `--out <dir>` (default `cauldron/images`), `--timeout`,
`--keep-log`. At most 5 images total across `--edit`, `--ref`, and the style's refs.

## Output layout

```
cauldron/
├── images/<slug>/
│   ├── prompt.md          # the spec you wrote for the latest run
│   ├── <slug>-1.png       # numbered, never overwritten (re-runs append -2, -3 …)
│   └── <slug>.json        # sidecar: every run's spec, refs, style text, thread id, outputs
└── styles/<name>.md       # art-style cards (see the art-style skill)
```

The script creates folders as needed. `cauldron/` is scratch space: if the project's
`.gitignore` does not cover it, say so once and let the user decide.

## Workflow

### 1. Preflight (first use in a session, or after any failure)

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/codex_image.py" doctor
```

If a check fails, relay the fix: `npm i -g @openai/codex` (missing), `codex logout && codex login`
(auth says api_key instead of ChatGPT), `codex --enable image_generation` or
`[features] image_generation = true` in `~/.codex/config.toml` (flag off).

### 2. Understand the request

- **Intent** — *generate* (no images, or images only as style/mood/composition references)
    vs *edit* (user wants an existing image changed while preserving the rest).
- **Images** — assign each a role: edit target → `--edit`; subject/composition reference →
    `--ref`; an art style → `--style cauldron/styles/<name>.md` (list with Glob). Use Read
    to look at any provided image before writing the spec so the prompt describes it well.
- **Slug** — short kebab-case name from the subject (`hero-banner`, `crane-blue`). Reuse
    the slug when iterating on the same asset so its history accumulates in one folder.
- **Size/format** — the built-in tool ignores exact pixel requests (outputs are roughly
    1024–1600 px). If the user needs exact dimensions, use `--fit WxH` (cover crops, contain
    fits inside) and `--format`.
- Ask only when a missing detail would make the result useless (e.g. required verbatim
    text, which of several images is the target). Otherwise decide and state assumptions.

### 3. Write the spec

Read [references/prompting.md](references/prompting.md) for the schema, taxonomy, and
augmentation rules. Write the spec to `cauldron/images/<slug>/prompt.md` using the
labeled lines that matter — typically `Use case`, `Primary request`, `Subject`,
`Style/medium`, `Composition/framing`, `Lighting/mood`, `Constraints`, `Avoid`.

- Keep the user's specifics verbatim; add detail only where a generic prompt needs it.
- Refer to attached images by index and role (`Image 1: edit target`) — the script lists
    them in that order.
- For edits, state invariants explicitly: `change only X; keep Y unchanged`.
- Text in the image: quote it verbatim and require exact rendering.
- Transparent background: ask for it explicitly and say to preserve alpha.
- Do **not** write the style block into the spec when using `--style`; the script appends
    the card itself.

### 4. Run

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/codex_image.py" generate \
    --prompt-file cauldron/images/<slug>/prompt.md --name <slug> \
    [--edit path] [--ref path] [--style cauldron/styles/<name>.md] [--count N] [--fit WxH]
```

A run takes roughly 1–3 minutes per image. Run it in the foreground with a generous
timeout; do not poll. Parse the JSON result: `ok`, `requested`, `outputs`, `final_message`,
`errors`. `ok` is false when fewer images than requested came back; the ones that did are
still in `outputs`.

If `ok` is false: read `errors` and `stderr_tail`. Missing tool or auth problems → run
`doctor`. A content/policy refusal → rephrase with the user. Anything odd → re-run once
with `--keep-log` and inspect `codex-last-run.jsonl`.

### 5. Review and iterate

Open every output with Read and judge it against the spec (subject, text accuracy,
invariants preserved, style adherence). Report what you see honestly.

To refine, prefer a single-change **edit** of the best output (`--edit <that file>` with a
spec that repeats the invariants) over regenerating from scratch. Keep the same slug.
Stop after the user's ask is met; do not burn quota on unrequested variants.

### 6. Report

List the output paths, one line on what each shows, the run time, and where the prompt
is recorded. Offer the obvious next step (variant, edit, fit to size, save as style).

## Rules

- Built-in tool only. If Codex reports the tool is unavailable, say so and run `doctor`;
    never fall back to the OpenAI API or a hand-written script.
- Never overwrite an existing output; the script numbers files for a reason.
- One `generate` call per distinct asset; use `--count` only for variants of one spec.
- Do not leave assets only in `~/.codex/generated_images` — the script copies them, and
    you reference the `cauldron/` paths.

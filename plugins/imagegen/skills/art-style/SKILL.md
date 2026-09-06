---
name: art-style
description: >-
  Create, list, inspect, and refine reusable art-style cards for image generation, stored
  as cauldron/styles/<name>.md with optional reference images. Use when the user wants to
  define a visual style, "save this look as a style", "make a style from these images",
  "what styles do I have", "tweak the <name> style", or wants consistent visuals across
  many generated images. Styles are applied by the generate-image skill via --style.
  Do NOT use for one-off image requests without a reusable style.
user-invocable: true
argument-hint: create <name> [description | --ref <img>...] | list | show <name> | sample <name>
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Art Style

A style card is a short markdown file that the `generate-image` skill appends to any
spec (`--style cauldron/styles/<name>.md`). Its optional reference images are attached
to the image tool as style references. Cards make a series of images look like they
belong together.

## Layout

```
cauldron/styles/
├── <name>.md            # the card
└── <name>/refs/         # optional, up to 3 reference images (png/jpg/webp)
```

Keep style refs to 3 so a generation still has room for its own edit target and
references (the tool caps at 5 images per call).

## Card format

```markdown
---
name: <name>
description: <one line - what the style looks like and what it suits>
created: <YYYY-MM-DD>
source: <"described" | "derived from N reference images" | "refined from <name>">
---
Style/medium: <e.g. flat vector illustration with subtle paper grain>
Color palette: <named colors or hex values; dominant vs accent>
Line & shape: <line weight, geometry, edge treatment>
Lighting/mood: <e.g. soft, even; muted; playful>
Materials/textures: <e.g. matte, grain overlay, no gradients>
Composition habits: <e.g. centered subject, generous negative space>
Rendering: <e.g. no outlines, no photorealism, no text>
Avoid: <what breaks the style>
```

Only the body (below the frontmatter) reaches the image model. Keep it under ~12 lines,
concrete and visual - describe what one *sees*, not adjectives like "modern" or "nice".

## Commands

### `create <name> <description>`

Write the card from the user's words. Expand a thin description into the concrete
lines above (palette, line, lighting, texture, composition, avoid). State what you
inferred so the user can correct it.

### `create <name> --ref <img>...`

Derive a style from images:

1. Read each image (the Read tool shows it to you). Note palette, line work, shading,
    texture, composition habits, and what is *absent*.
2. Write the card describing the shared look - not the subjects in the images.
3. Copy up to 3 of the images into `cauldron/styles/<name>/refs/` (Bash `cp`). Prefer the
    ones that best represent the style on their own.

### `list`

Glob `cauldron/styles/*.md`, print each card's name, description, and whether it has refs.

### `show <name>`

Print the card and list its refs.

### `sample <name>`

Validate a card by rendering one test image with it. Write a neutral spec (e.g. "a lone
lighthouse on a rocky coast at dusk", `Use case: stylized-concept`) to
`cauldron/images/style-sample-<name>/prompt.md`, then:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/codex_image.py" generate \
    --prompt-file cauldron/images/style-sample-<name>/prompt.md \
    --name style-sample-<name> --style cauldron/styles/<name>.md
```

Read the output, compare it against the card, and propose concrete edits to the card if
the look drifted. Do not run more than one sample unless asked; each costs quota.

### Refining

Edit the card in place with the Edit tool, bump nothing - cards are not versioned. If
the user wants to keep the old look, copy the card to a new name first.

## Rules

- Never invent brand names, artist names, or trademarks in a card unless the user gave
    them. Describe the look instead ("thick black outlines, flat cel shading").
- Cards are project-local scratch under `cauldron/`; mention once if it is not gitignored
    and let the user decide.
- Applying a style is the `generate-image` skill's job; from here, hand off with the
    exact `--style` path.

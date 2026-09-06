# Prompting reference

How to turn a request into a spec the image model executes well. Principles distilled from
OpenAI's bundled Codex imagegen skill (Apache-2.0), trimmed to what applies to the
built-in tool.

## Structure

Order the spec scene → subject → details → constraints → intended use. Use short labeled
lines, not one long paragraph. Only include lines that carry information.

```text
Use case: <taxonomy slug>
Asset type: <where the asset will be used>
Primary request: <the user's ask, kept verbatim where specific>
Input images: <Image 1: role; Image 2: role>            (only when images are attached)
Scene/backdrop: <environment>
Subject: <main subject, concrete>
Style/medium: <photo / illustration / 3D / painterly …>  (omit when a style card is used)
Composition/framing: <wide / close-up / top-down; placement; negative space>
Lighting/mood: <light + atmosphere>
Color palette: <notes>
Materials/textures: <surface details>
Text (verbatim): "<exact text>"                          (only when text must appear)
Constraints: <must keep / must avoid>
Avoid: <negative constraints>
```

## Specificity policy

- **Detailed prompt** → normalize into the structure; add nothing creative.
- **Generic prompt** → add tasteful detail only where it materially improves the result:
    framing, polish level, intended use, reasonable scene concreteness.
- Never add: extra characters, props, brands, slogans, palettes, narrative beats, or
    left/right placement the request does not imply.

## Use-case taxonomy

Generate: `photorealistic-natural`, `product-mockup`, `ui-mockup`, `infographic-diagram`,
`scientific-educational`, `ads-marketing`, `productivity-visual`, `logo-brand`,
`illustration-story`, `stylized-concept`, `historical-scene`.

Edit: `text-localization`, `identity-preserve`, `precise-object-edit`, `lighting-weather`,
`background-extraction`, `style-transfer`, `compositing`, `sketch-to-render`.

## Tips by use case

- **photorealistic-natural** — say `photorealistic`; use camera language (lens, depth of
    field, framing); ask for real texture (pores, fabric wear, grain); avoid glossy polish.
- **product-mockup** — describe materials and silhouette; label text verbatim with
    typography notes; clean backdrop; no trademarks unless supplied.
- **ui-mockup** — state fidelity first (wireframe vs shippable); focus on layout and
    hierarchy; no concept-art language.
- **infographic-diagram / productivity-visual** — audience, reading flow, exact labels,
    readable typography, whitespace.
- **logo-brand** — simple, scalable, strong silhouette, balanced negative space.
- **illustration-story / stylized-concept** — concrete scene beats; style cues, material
    finish, rendering approach (3D, painterly, clay) without inventing story.
- **historical-scene** — place and date; constrain clothing, props, environment to the era.

Edits: always list invariants (`change only the paper color; keep pose, folds, lighting, framing and background unchanged`) and repeat them on every iteration. For compositing,
say what moves where and demand matched lighting, perspective, and scale. For cutouts,
require a genuinely transparent background with clean edges and no halos.

## Text in images

Quote literal text, specify font style/size/color/placement, spell unusual words
letter-by-letter, and require verbatim rendering with no extra characters.

## Reference images

- Not every attached image is an edit target. Label each by index and role.
- Style references: "match the look (palette, line work, texture) of Image N; do not copy
    its subject or composition."
- Composition references: "use the framing/pose of Image N with the new subject."
- At most 5 images per call, including a style card's references.

## Iterating

Start from a clean base spec, then make one targeted change per run, editing the best
output rather than regenerating. Re-state critical constraints each time.

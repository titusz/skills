---
name: evaluate-startup
description: >-
  Run a rigorous, research-backed evaluation of a startup or business idea and produce a
  scored analysis.json, a polished standalone HTML report, and a searchable index of all
  evaluations. Use whenever the user wants to evaluate, score, vet, compare, or stress-test
  a startup idea, business opportunity, product concept, side-project bet, or asks "is this
  worth building / pursuing?" — also when they invoke /evaluate-startup or mention
  opportunity scouting, idea evaluation, or their startup-ideas cauldron. Runs an adaptive
  founder interview, parallel deep research, adversarial fact-checking, and renders results
  with the bundled render.py script. Do NOT use for reviewing existing code, valuing public
  companies, or general market research that needs no go/no-go verdict.
user-invocable: true
argument-hint: <idea description> [--out <dir>] [--instructions "..."]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, WebSearch, WebFetch, AskUserQuestion
---

# Evaluate Startup

Turn a raw startup idea into an evidence-backed, scored evaluation with a durable,
browsable artifact trail. The output is a decision aid, not a cheerleading document:
honest scores, falsifiable assumptions, explicit kill criteria.

## Tooling

All validate/render/index commands below use the bundled script:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/evaluate-startup/scripts/render.py" <command> ...
```

Abbreviated as `render.py` in the phases. If `${CLAUDE_PLUGIN_ROOT}` is not set in your
environment, resolve the script path relative to this SKILL.md file.

## Arguments

`$ARGUMENTS` may contain, in free-form order (all optional):

- **Idea description** — anything from a one-liner to a full pitch. If absent, ask for it.
- **Output path** — e.g. `--out ./somewhere` or "store results in X".
    Default: `./startup-ideas`
- **Custom instructions** — e.g. `--instructions "..."` or natural language like
    "focus on the EU market" or "add a competitor pricing matrix to the report".
    These tailor the interview, research angles, scoring weights, and report extras.

Interpret naturally; do not demand exact flag syntax.

## Output layout

```
<output-root>/
├── index.html                     # searchable card index (auto-regenerated)
└── <idea-slug>/
    ├── analysis.json              # canonical latest evaluation
    ├── report.html                # rendered standalone report
    └── history/                   # prior runs, timestamped (on re-evaluation)
        └── analysis-20260806T120000Z.json
```

Slug: lowercase, hyphenated, from the idea name (e.g. "Freight Invoice Audit Agent" →
`freight-invoice-audit-agent`). If a directory with `analysis.json` already exists for
this idea, this is a **re-evaluation**: move the old `analysis.json` into `history/`
before writing the new one. Never silently overwrite an evaluation.

The archive filename is `analysis-<stamp>.json`, where `<stamp>` is the old file's
`evaluated_at` with `-` and `:` stripped (`2026-08-06T12:00:00Z` → `20260806T120000Z`).
Colons are illegal in Windows filenames, so never use the raw RFC 3339 value.

## Workflow

Execute phases in order. Announce each phase briefly so the user can follow along.

### Phase A — Adaptive interview

Goal: capture the founder's **opinionated intent** — what they believe, what they want,
what they'd refuse to do — plus close real information gaps. Full guidance and question
bank: read [references/interview-guide.md](references/interview-guide.md).

Rules of engagement:

- **Adaptive, not ritual.** First extract everything already answered by the provided
    description and conversation context. Only ask about genuine gaps. A rich description
    may need just one batch; a one-liner needs all three.
- Up to **3 batches of at most 3 questions** (use AskUserQuestion when available,
    otherwise plain numbered questions). Never exceed 9 questions total.
- **Plain language.** No jargon the user must decode (no "TAM", "CAC", "moat" unless
    they used it first). Ask about their world, not about frameworks.
- Probe for unknown unknowns: constraints they haven't stated, the failure they fear,
    what they'd consider a waste of a year.
- If the user says "just proceed", fill gaps with clearly-labeled assumptions in the
    analysis rather than stalling.

### Phase B — Parallel deep research

Goal: independent, sourced evidence. Read
[references/research-guide.md](references/research-guide.md) for the five standard
research angles and per-agent briefs, then spawn one subagent per angle **in parallel**
(Task tool). Adjust or add angles per custom instructions and idea specifics.

- Each subagent returns: summary, key findings, and sources (title + URL + note).
- **No subagents available** (e.g. claude.ai): run the angles sequentially yourself with
    WebSearch/WebFetch — trim to the 3 highest-value angles to keep the run reasonable.
- Prefer primary sources. Mark estimates as estimates. A finding without a source is an
    opinion — keep those in the assessment, not in research.

### Phase C — Analysis

Read [references/methodology.md](references/methodology.md) — it defines the scoring
model (6 categories, dimensions, weights, score anchors, conviction, verdict bands).
Then write `<idea-slug>/analysis.json` conforming to `scripts/analysis.schema.json`.
A complete worked example: [references/example-analysis.json](references/example-analysis.json).

- Score against the anchors, not against enthusiasm. Most real ideas land 4–7.
- Every dimension rationale must be specific to *this* idea — no template filler.
- Curate the most relevant sources into each assessment category's `sources` array
    (the raw research stays in the `research` block as an appendix).
- Compute `scores.composite` (Σ weight × score) and `scores.conviction` (weighted
    confidence) exactly as methodology.md specifies; the validator will check your math.

Validate immediately:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/evaluate-startup/scripts/render.py" validate <path>/analysis.json
```

Fix every reported problem before proceeding.

### Phase D — Adversarial review

Spawn 2–3 reviewer subagents in parallel (or do sequential passes yourself if no
subagents), each with a narrow brief:

1. **Fact-checker** — verify every factual claim in the analysis against its cited
    sources (re-fetch if needed). Flag unsupported numbers, stale data, invented sources.
2. **Consistency auditor** — do scores match their rationales? Does the verdict follow
    from the scores and the methodology's verdict logic? Are strengths/risks consistent
    with category findings?
3. **Devil's advocate** — steelman the case *against* the current verdict. What did the
    analysis conveniently ignore?

Integrate the findings: fix errors, adjust scores where challenged successfully, add
overlooked risks. Re-run `validate` after edits. Note material changes to the user.

### Phase E — Render report

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/evaluate-startup/scripts/render.py" render <path>/analysis.json
```

This produces a self-contained `report.html` (light/dark toggle, offline, printable).
Then consider **custom sections**: if the idea would benefit from a bespoke visualization
(competitor pricing matrix, market timeline, unit-economics calculator, geographic
breakdown…), or if custom instructions requested one, add it to the JSON's
`custom_sections` array as `{"title": ..., "html": ...}` (self-contained inline
HTML/SVG/JS, matching the report's CSS variables like `var(--panel-2)`, `var(--text)`,
`var(--border)`) and re-render. Custom sections are for genuine idea-specific value —
skip them when the standard report already tells the story.

### Phase F — Index

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/evaluate-startup/scripts/render.py" index <output-root>
```

Regenerates `index.html` by scanning `<output-root>/*/analysis.json` — searchable,
sortable cards linking to each report. Always run this last so the index stays complete.

(`render.py all <path>/analysis.json` chains validate + render + index when convenient.)

### Phase G — Present

Close with a compact summary in chat: verdict badge + composite + conviction, the 2–3
decisive factors, the single most important assumption to validate next, and the file
paths. Do not paste the whole report into chat.

## Quality bar

- The evaluation must be able to **hurt**. If every idea comes out "prototype or
    better", the tool is worthless. An unflinching "monitor" with clear kill criteria is
    a more valuable output than a flattering 8.
- Distinguish **attractiveness** (composite) from **conviction** (evidence strength).
    A great-looking idea on thin evidence gets "validate", not "pursue".
- Keep the user's own words in `interview_notes` — future re-evaluations depend on them.
- If the run is interrupted, partial artifacts (analysis.json without report) are fine;
    the index gracefully links whatever exists.

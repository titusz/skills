# Research Guide

Purpose: gather independent, sourced evidence before scoring. Research feeds
`research.angles[]` verbatim and, curated, the per-category `sources` arrays.

## Standard angles (spawn one subagent each, in parallel)

Adjust titles/briefs to the idea; add angles when custom instructions or the interview
reveal a decisive unknown (e.g. "EU regulatory landscape" for a fintech idea). When no
subagents are available, run the top 3 angles yourself sequentially — usually
`market`, `competitors`, and whichever of the rest the verdict most depends on.

| id            | Title                                   | Mission                                               |
| ------------- | --------------------------------------- | ----------------------------------------------------- |
| `market`      | Market size & demand                    | Realistic serviceable market, growth, demand signals  |
| `competitors` | Competitors & alternatives              | Who solves this today, how well, at what price        |
| `technology`  | Technology & state of the art           | Feasibility, quality bars, what just became possible  |
| `customers`   | Customer economics & willingness to pay | What buyers spend now, budget owners, pricing analogs |
| `timing`      | Regulation & timing                     | Legal constraints, tailwinds, why-now catalysts       |

## Subagent brief template

```
You are researching one angle for a startup-idea evaluation. Work independently.

IDEA: <one_liner + 3-5 sentence description + target customer>
ANGLE: <title> — <mission, tailored to this idea>
CUSTOM FOCUS: <relevant custom instructions, if any>

Tasks:
1. Search broadly, then drill into the 3-5 most load-bearing questions for this angle.
2. Prefer primary sources (industry reports, government data, company filings, pricing
   pages, technical papers) over blog rehashes. Note publication dates; flag stale data.
3. Distinguish facts (sourced) from estimates (labeled) from your inferences (labeled).
4. Actively look for DISCONFIRMING evidence — failed attempts, shutdown post-mortems,
   negative analyst takes. One honest red flag is worth five confirmations.

Return exactly this structure:
- summary: one paragraph, the "so what" for an investor
- findings: 5-10 bullet points, each a specific, decision-relevant fact or insight
- sources: list of {title, url, note} — note says what the source supports
```

## Standards of evidence

- A number without a source and date is an estimate — label it.
- Two independent sources disagreeing is itself a finding — record both.
- Absence of evidence after honest search is a finding ("no public pricing found for
    any competitor") — it lowers conviction, which is exactly what conviction is for.
- Never invent sources. A fabricated citation is the one unforgivable output; the
    fact-checker in Phase D re-fetches URLs.

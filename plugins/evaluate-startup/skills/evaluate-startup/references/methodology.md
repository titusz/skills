# Scoring Methodology (schema v1.0)

The model separates two questions that most evaluation frameworks conflate:

1. **Attractiveness** — how good is this idea if the claims hold? → `scores.composite` (0–10)
2. **Conviction** — how strong is the evidence behind the claims? → `scores.conviction` (0–1)

An idea can be attractive on thin evidence (→ validate, don't commit) or unattractive on
solid evidence (→ confidently avoid). Keeping the axes apart is what makes the verdict
honest.

## Categories and default weights

Six categories, each scored 0–10 with a confidence level and 3–5 dimensions.
Weights live **in the JSON** so every report is self-explaining; adjust them only when
the user's custom instructions justify it (note the adjustment in `verdict.summary`).

| #   | Category (id)                               | Weight | Core question                                                               |
| --- | ------------------------------------------- | ------ | --------------------------------------------------------------------------- |
| 1   | Problem & Demand (`problem`)                | 0.20   | Is this a burning, frequent, specific problem someone already pays to ease? |
| 2   | Market & Timing (`market`)                  | 0.15   | Is the reachable market real and is *now* the moment?                       |
| 3   | Solution & Automation Leverage (`leverage`) | 0.25   | Can the core value loop run mostly on its own, with verifiable outcomes?    |
| 4   | Competition & Moat (`moat`)                 | 0.15   | Can this win attention and *stay* defensible?                               |
| 5   | Business & Economics (`economics`)          | 0.10   | Does money flow cleanly and scale better than costs?                        |
| 6   | Execution & Fit (`execution`)               | 0.15   | Can *this* founder ship it, and does the path avoid quicksand?              |

### Standard dimensions per category

Use these dimensions by default; rename/replace individual ones when the idea demands it
(keep 3–5 per category, ids lowercase snake_case).

**1. Problem & Demand** — `pain_intensity` (vitamin vs. painkiller vs. fire),
`frequency_urgency` (daily fire vs. annual annoyance), `problem_specificity` (crisp,
nameable problem vs. vague unease), `demand_evidence` (people already spending
money/time on workarounds?).

**2. Market & Timing** — `reachable_market` (realism of the serviceable market, not the
headline TAM), `growth_trajectory` (growing, flat, dying?), `why_now` (what changed —
technology, regulation, behavior — that makes this newly possible?), `tailwinds`
(macro/regulatory forces helping or hurting).

**3. Solution & Automation Leverage** — the heart of the framework, derived from
"current state → ideal state via verifiable iteration":

- `outcome_verifiability` — can success be checked unambiguously, ideally automatically?
    (tests pass = 10 … "feels better" = 2). This is foundational: it enables automated
    feedback loops, confident scaling, and low-oversight operation.
- `error_tolerance` — cost and blast radius of a mistake. A false positive costing a
    5-minute review scores high; an irreversible customer-facing error scores low.
- `feedback_loop_speed` — how fast does reality answer back? Seconds/hours high;
    quarters low.
- `scope_decomposability` — does the ambitious goal break into small, independently
    verifiable subtasks (a healthy gap between where goals are set and where work is
    executed)? Clean decomposition means errors get caught before they roll up.
- `data_context_availability` — is the information the system needs actually
    accessible (APIs, documents, permissions), or trapped in heads and silos?

For non-AI ideas this category still applies: score how much of the value loop can be
systematized, measured, and improved without heroic manual effort.

**4. Competition & Moat** — `competitive_intensity` (crowded vs. open field; "no
competitors" usually means "no market"), `differentiation` (10x on something buyers
care about?), `defensibility` (what compounds over time: data, network, standards,
switching costs), `platform_risk` (can an incumbent kill it with a feature or a
policy change?).

**5. Business & Economics** — `revenue_clarity` (who pays, for what, when),
`unit_economics` (plausible margin per unit of value delivered), `scalability`
(does revenue outrun cost and headcount?), `capital_intensity` (bootstrappable vs.
needs a war chest before signal).

**6. Execution & Fit** — `technical_feasibility` (buildable with current tech at
current quality bars), `mvp_effort` (smallest honest test: days/weeks high, quarters
low), `founder_advantage` (unfair advantage: domain depth, distribution, credibility,
assets), `regulatory_dependency_drag` (approvals, gatekeepers, single points of
external failure).

## Score anchors

Score against anchors, not vibes. Most real ideas land 4–7; a 9+ needs evidence.

| Range | Meaning                                 |
| ----- | --------------------------------------- |
| 0–2   | Fatal flaw; disqualifying on its own    |
| 3–4   | Weak; a real drag that needs a plan     |
| 5–6   | Average; neither helps nor hurts        |
| 7–8   | Strong; genuine advantage               |
| 9–10  | Exceptional; rare, evidence-backed edge |

Category score = your judgment anchored by the dimension scores (validator flags a
deviation > 1.5 from the dimension mean — justify or fix).

## Composite, conviction, band

```
composite  = Σ (weight_i × score_i)                    # 0–10, two decimals
conviction = Σ (weight_i × conf_i) / Σ weight_i        # conf: high=1.0, medium=0.6, low=0.3
```

Confidence per category reflects **evidence quality** for that category's claims
(sourced data = high; reasonable inference = medium; guesswork = low). It is not how
much you like the idea.

### Verdict logic

| Composite | Conviction ≥ 0.5 | Conviction < 0.5 |
| --------- | ---------------- | ---------------- |
| ≥ 7.5     | `pursue`         | `validate`       |
| 6.5 – 7.4 | `prototype`      | `validate`       |
| 5.5 – 6.4 | `explore`        | `explore`        |
| 4.0 – 5.4 | `monitor`        | `monitor`        |
| < 4.0     | `avoid`          | `monitor`\*      |

\* A very low score on very weak evidence is a "probably not, but we barely looked" —
`monitor` with pointed validation questions beats a false-confidence `avoid`.

`scores.band` follows this table mechanically. `verdict.recommendation` is your final
judgment — it usually equals the band, but you may deviate one step with explicit
reasoning in `verdict.summary` (e.g., a single critical risk caps an otherwise strong
idea). Never deviate more than one step.

## Verdict block guidance

- **strengths / weaknesses** — 3–5 each, concrete, traceable to category findings.
- **risks** — severity = damage if it happens; likelihood = odds it happens. Include at
    least one risk with a straight face even for great ideas.
- **assumptions** — the load-bearing beliefs. Each must be falsifiable; `current_evidence`
    states what (if anything) supports it today.
- **kill_criteria** — observable facts that, if true, mean stop. Write them so a future
    re-evaluation can check them mechanically.
- **validation_plan** — cheapest experiments that attack the highest-criticality
    assumptions first. Method + effort + an unambiguous success signal.
- **next_steps** — 3–6 ordered, immediately actionable items.

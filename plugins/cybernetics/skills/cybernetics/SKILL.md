---
name: cybernetics
description: >-
  Review an idea, concept, system, challenge, or problem against the 8 rules of
  bio-cybernetics (Frederic Vester) and report on its viability. Maps the
  subject's feedback loops, scores each of the 8 rules (aligned / at-risk /
  violated), surfaces the 2-3 highest-leverage fixes, and judges whether the
  design is self-sustaining or on a path to runaway growth, brittleness, energy
  waste, or collapse. Use when asked to "apply bio-cybernetics", "do a cybernetic
  review", "check Vester's rules", "is this sustainable / viable / will it scale
  without collapsing", "find the feedback loops", or to pressure-test the
  long-term health of a product, business model, org design, policy, or
  architecture. Do NOT use for routine tasks with an obvious agreed solution.
user-invocable: true
argument-hint: <idea, concept, system, challenge, or problem to review>
---

# Bio-Cybernetics Review

Judge whether a thing will *stay alive*. Living systems that survive over time
share a small set of design principles; Frederic Vester distilled them into
**8 bio-cybernetic rules**. This skill treats the subject — an idea, product,
business model, org, policy, or architecture — as a living system embedded in a
larger one, maps its feedback loops, and scores it against the 8 rules. A subject
that honors them tends to be resilient and self-sustaining; one that breaks them
tends to grow brittle, waste energy, or crash when a higher-order loop intervenes.

> The 8 rules below are **Frederic Vester's biocybernetic rules** (from *Die
> Kunst, vernetzt zu denken* / "The Art of Interconnected Thinking"). This skill
> turns them into a review and improvement diagnostic.

## What this skill produces

Given a subject, output a structured review: the subject as a system → its
feedback map → a per-rule scorecard → the highest-leverage fixes → an overall
viability verdict → signals to watch. Fill the [output template](#output-template).

For deep rule cards with Vester's original examples, violation signals, and a
worked example, read `references/biocybernetics-field-guide.md` when a call is
non-obvious or you want the source illustrations.

## How cybernetics differs from systems-thinking

They compose well but answer different questions. **systems-thinking** *classifies*
a problem (clear/complicated/complex/chaotic) and picks the right action protocol.
**cybernetics** *evaluates the viability* of a system's design against 8 specific
bio-inspired rules and proposes redesigns. Reach for this skill when the question
is "will this survive and stay healthy over time, and how do I make it more so?"

## Step 1 — Frame the subject as a living system

A bio-cybernetic review only works once the subject is stated as a system. In one
line each:

- **Subject** — what it is.
- **Function** — the need it actually serves (not the product/form it currently takes — this matters for Rule 3).
- **Enclosing system** — the higher-order system it lives inside (its market, ecosystem, body politic, environment). Rule 1 turns on this: when a subsystem's own brakes fail, a *higher* regulating circuit intervenes — often by killing it.

If you can't name the function and the enclosing system, get those before scoring.

## Step 2 — Map the feedback loops

Feedback is the spine of cybernetics (Rules 1 and 8 are explicitly about it).
Name the loops driving the subject's behavior:

- **Reinforcing (positive) loops** — self-amplifying: more → more (growth, virality, accumulation, arms races).
- **Balancing (negative) loops** — self-regulating: deviation triggers correction (saturation, price, fatigue, quotas, predators). These are the *governors*.
- **Dominant loop today** — which one actually drives current behavior, and what happens if it keeps dominating.

## Step 3 — Score the 8 rules

For each rule give a verdict, the evidence, and the leverage move. Use the scale:
**✓ Aligned** · **⚠ At risk** · **✗ Violated** · **– N/A**. Don't force all eight
to apply — mark **N/A** honestly; the value is in the few that bite.

| #   | Rule                                                | What to check                                                                                                  | Violation signal                                                                                                             | Leverage move                                                                                                                    |
| --- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Negative feedback dominates positive**            | Do balancing loops cap the reinforcing ones? Is the regulator part of the system?                              | Unbounded growth; "more is always better"; no circuit breaker; success accelerates with no brake.                            | Build in self-limiting loops (quotas, price signals, saturation, rest cycles) *before* a higher loop crashes it.                 |
| 2   | **Vitality independent of quantitative growth**     | Does survival depend on perpetual growth? Has added size/connectivity started to *reduce* stability?           | Growth is the goal; metamorphosis avoided; ever-more connections breeding fragility or chaos.                                | Switch from growing to *developing* — metamorphose; find the optimal, not maximal, size and connectivity.                        |
| 3   | **Function-oriented, not product-oriented**         | Is identity bound to a specific product/form, or to the function it serves?                                    | "We *are* our product"; can't imagine surviving the product's obsolescence.                                                  | Reframe around the job-to-be-done; dare to question the product itself (the VW Beetle won on global service).                    |
| 4   | **Use existing forces (jiu-jitsu, not boxing)**     | Is the system spending energy fighting forces it could ride?                                                   | Brute-force control against gradients (air-conditioning the heat you generated); fighting momentum head-on.                  | Redirect existing flows — sun/wind/waste-heat, market momentum, people's existing motivation — for low steering energy.          |
| 5   | **Multiple use of products, functions, structures** | Do elements each serve one purpose where they could serve several?                                             | Single-purpose components; siloed structures; "one tool, one job" everywhere.                                                | Combine functions (combined heat-and-power, dual-use parts, one team many roles) — two birds, one stone.                         |
| 6   | **Recycling — use waste and byproducts**            | Are waste/byproduct streams discarded instead of fed back?                                                     | Linear take-make-dispose; outputs leave as loss; "waste" treated as inevitable.                                              | Close loops — every output is some process's input. Nature has no waste; every product has its enzyme.                           |
| 7   | **Symbiosis — mutual use of difference**            | Could complementary partners couple and exchange to save energy/resources? Is it needlessly autarkic?          | Doing everything alone; ignoring partners whose differences complement; centralizing where exchange would save.              | Form symbioses — couple with the *different* (the mitochondrion's bargain); prefer many small local exchanges.                   |
| 8   | **Biological design via feedback planning**         | Is the design compatible with humans and nature? Does it connect things without structure, propagating faults? | Connect-everything-to-everything with no insulation; designs hostile to people/environment; plan-then-ship with no feedback. | Design iteratively with feedback; add structure/insulation so interference doesn't spread; keep it human- and nature-compatible. |

## Step 4 — Find the highest-leverage fixes

Cybernetics is about leverage: where does a small change yield a large, system-wide
improvement? Of the rules scored **⚠** or **✗**, pick the **2-3** that, if fixed,
most improve viability — usually the ones touching the *dominant loop* from Step 2.
Rank them; don't dilute the report with all eight.

## Step 5 — Render the viability verdict

Synthesize one judgment of whether the subject will survive and stay healthy, and
name the dominant failure path if nothing changes. Useful labels:

- **Self-sustaining** — balancing loops govern; honors most rules.
- **Brittle growth** — alive only while it grows; metamorphosis overdue (Rule 2).
- **Runaway risk** — a reinforcing loop with no governor; a higher loop will eventually correct it hard (Rule 1).
- **Energy-wasteful** — fights forces it could ride; leaks waste it could recycle (Rules 4, 6).
- **Isolated** — autarkic where symbiosis would save it (Rule 7).

## Step 6 — Name the signals to watch

For each top risk, give one leading indicator that would confirm or refute the
read early — the cheap measurement that reveals whether the missing loop is
actually biting (e.g., for Rule 1, track the quantity that's growing unchecked, not
the headline that looks healthy).

## Output template

```markdown
## Subject
<one line> — function: <need it serves> — embedded in: <enclosing system>

## Feedback map
- Reinforcing (positive) loops: ...
- Balancing (negative) loops: ...
- Dominant loop today: <which drives behavior, and where it leads>

## Bio-cybernetic scorecard
| # | Rule | Verdict | Evidence | Leverage move |
|---|------|---------|----------|---------------|
| 1 | Negative feedback dominates             | ✓/⚠/✗/– | ... | ... |
| 2 | Vitality independent of growth          | ✓/⚠/✗/– | ... | ... |
| 3 | Function- not product-oriented          | ✓/⚠/✗/– | ... | ... |
| 4 | Use existing forces (jiu-jitsu)         | ✓/⚠/✗/– | ... | ... |
| 5 | Multiple use                            | ✓/⚠/✗/– | ... | ... |
| 6 | Recycling                               | ✓/⚠/✗/– | ... | ... |
| 7 | Symbiosis                               | ✓/⚠/✗/– | ... | ... |
| 8 | Biological / feedback design            | ✓/⚠/✗/– | ... | ... |

## Highest-leverage fixes
1. Rule <#> — <the change, and why it pays off most>
2. Rule <#> — ...

## Viability verdict
<self-sustaining | brittle growth | runaway risk | energy-wasteful | isolated> —
<one paragraph: will it survive and stay healthy, and the dominant failure path if unchanged>

## Watch signals
- <top risk> → leading indicator: ...
```

## Notes

- Keep the review proportional to the stakes — a small idea gets a few lines and its 2-3 live rules, not the whole template.
- The point is not a high score; it's finding the one or two loops whose redesign changes the trajectory. A subject can violate several rules and still be saved by fixing the dominant one.
- Rules 1 and 2 are about *staying viable*; 3 keeps you flexible; 4-7 are about *efficiency through connection* (forces, multi-use, recycling, symbiosis); 8 is about *designing with feedback and fit*. If short on space, lead with whichever cluster the subject most violates.
- If essential parts are unknown (the function, the enclosing system, the real loops), say what you'd need to observe rather than guessing.

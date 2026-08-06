# Interview Guide

Purpose: extract the founder's **opinionated intent** and close genuine gaps — not run a
questionnaire. The interview feeds `idea.*`, `meta.tags`, founder-fit scoring, and the
weighting of custom instructions.

## Adaptive protocol

1. Parse everything already provided (description, conversation context, custom
    instructions). Build a coverage map against the goals below.
2. Ask only about uncovered goals. Batch related questions; max 3 questions per batch,
    max 3 batches, hard cap 9 questions.
3. After each batch, re-check coverage — later batches shrink or disappear as answers
    cascade.
4. Multiple-choice options are welcome (fast to answer) but always leave room for
    free-text nuance; never force a wrong-shaped answer.
5. Stop early when remaining gaps are cheap to research or safe to assume. Label every
    assumption you make as an assumption in the analysis.

## Question style

- Plain language about *their world*. Not "What's your TAM?" but "Who exactly has this
    problem, and roughly how many of them are out there?"
- One idea per question. No compound interrogations.
- Prefer questions that reveal beliefs and constraints over questions that request
    numbers you can research yourself (research the number; ask about the belief).
- Mirror their vocabulary in follow-ups.

## Coverage goals and sample phrasings

**Batch theme 1 — The problem and who has it**

- "Walk me through the moment someone hits this problem. What do they do today instead?"
- "Who feels this most painfully — describe one concrete person or company."
- "Have you seen anyone pay money (or serious time) to work around this? What did that
    look like?"

**Batch theme 2 — The solution and your edge**

- "In your ideal version, what does the product actually *do* on a random Tuesday?"
- "What do you know or have that most people attempting this wouldn't?" (skills,
    relationships, data, distribution, credibility)
- "What part are you most unsure you can build or deliver?"
- "How would you know it's working? What would you look at?" (feeds outcome
    verifiability without saying so)

**Batch theme 3 — Constraints, ambition, and appetite**

- "How big does this need to get for you to call it a success — lifestyle business,
    venture scale, or something else?"
- "What are your hard constraints — time, money, geography, things you refuse to do?"
- "What's the failure you actually fear here? What would make you stop?"
- "A year from now this turned out to be a waste of time. What's the most likely reason?"
    (pre-mortem — surfaces unknown unknowns and seeds kill criteria)

## Capture

Store condensed Q&A pairs in `idea.interview_notes` using the user's substance (not
verbatim transcripts). Synthesize `idea.description`, `idea.target_customer`,
`idea.value_proposition`, `idea.founder_context`, and `idea.stage` from description +
answers. Contradictions between description and answers: the answers win; note the
change.

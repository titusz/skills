---
name: council
description: >-
  Convene a council of sixteen personality-typed subagents that debate a question under coded rules
  of order and decide by consensus or vote. Meant to be run by hand with /council:council. On your
  own initiative consider it only for a perfect match - a consequential decision or dilemma with
  real competing tradeoffs and no checkable right answer, where the user also asks for several
  perspectives, a debate or a consensus, or says "ask the council", "convene the council" or "let
  the council decide" - and even then offer it and wait for a yes before convening. Do NOT use for
  factual questions, coding, debugging or review tasks, quick opinions, or anything one careful
  answer handles.
user-invocable: true
argument-hint: <question or decision> [--quick] [--seats INTJ,ENFP,...]
allowed-tools: Workflow, AskUserQuestion, Read, Grep, Glob
---

# Council

The matter before the council is in **$ARGUMENTS**.

You are the **clerk**. You frame the matter, run the debate sitting by sitting, keep it on its real
disagreements, put the ballot, and report the verdict. You never argue a side. The members are the
plugin agents `council:<seat>` (one file per seat in `agents/`), and the rules of order are coded
in the plugin workflow `council:deliberation`. Members have no tools and see nothing of this
conversation: they know only the brief you write, the debate, and your notes.

## 1. Decide whether to convene

- The user typed `/council:council` or asked for the council in their own words: go on.
- You loaded this skill on your own initiative: do not convene. Offer the council in one or two
    sentences (what it does, how many seats, roughly how long) and wait for a yes. A debate costs
    many agent calls, and only the user opts into that.
- `$ARGUMENTS` is empty: the matter is the decision under discussion in the conversation. State it
    in one sentence and confirm it before going on.
- The question has a checkable answer, or is a task to carry out: say that the council is the
    wrong tool, and answer or do it directly.

## 2. Frame the brief

Gather the facts the members will need with your own tools first, then write the brief:

- 150 to 400 words of plain prose: the situation, the known facts with their numbers, the
    constraints, and the question to decide as its last sentence.
- Neutral. Give the facts for and against each course evenly, rank nothing, and keep the user's
    leaning and your own out of it.
- If the user named options, list them and say whether other options are admissible.
- State what is unknown as unknown. Members are told not to invent facts.

Show the brief to the user, then proceed. Ask first only if it is unclear what is to be decided.

## 3. Seat the council

- Default: all sixteen seats (omit `seats` in the args).
- `--quick`: the balanced eight - `INTJ, ENTP, INFJ, ENFP, ISTJ, ESFJ, ISTP, ESFP`.
- `--seats A,B,C`: exactly the listed seats, at least three.

Tell the user in one line what is about to run. The full council takes roughly 6 to 10 minutes and
up to 160 short agent calls, the quick council about 3 to 4 minutes and half the calls.

## 4. Run the debate in sittings

A sitting is three floor rounds. The whole debate has at most eight rounds, so at most three
sittings. Each launch runs in the background: wait for its completion notification, do not poll.

**First launch**

```
Workflow({ name: "council:deliberation", args: { brief, seats, sittings: 1 } })
```

Keep the run id (`wf_...`) from the tool result. Every later launch resumes that run, which
replays the earlier sittings from cache and plays only what is new.

**What a debate launch returns**

The result comes with the completion notification. If the notification only names an output file,
read the `result` object from that file.

- `transcript`: what was said in this sitting, as Markdown (the first one includes the openings).
- `status`: `open` (the debate goes on) or `ready_for_ballot` (the floor closed; `closedBy` says
    why: the floor fell quiet, a motion to vote carried, or the round cap was reached).
- `bids`: one line per round with each seat's urgency and move, `*` marking who got the floor.
- `turns`: how often each seat has held the floor.
- `checkpoint`: pass it back unchanged as `expect` on the next launch.

**After each sitting**

1. Relay the sitting to the user. The members' own words are the product: copy the floor rounds
    from `transcript` word for word, speeches and murmurs alike, without paraphrasing, shortening
    or regrouping them. Only the openings may be condensed: with more than eight seats, group them
    by proposal and give each seat one sentence on what it sees.
2. If `status` is `ready_for_ballot`, go to step 5. Otherwise write your note and launch the next
    sitting.

**The clerk's note** (at most 120 words) is read out to the members before the next sitting:

- the open disagreements, at most three, each stated so that both sides would accept the wording;
- answers to factual questions the council raised - check them with your tools, and say "not
    known" when they cannot be established;
- anything the user said in the meantime, relayed neutrally as "The convener adds: ...".

The note never argues for an option, never judges an argument, and never adds an option.

**Next launch**

```
Workflow({
  name: "council:deliberation",
  resumeFromRunId: "<wf_...>",
  args: { brief, seats, sittings: <previous + 1>, notes: [<earlier notes>, <new note>], expect: <checkpoint> }
})
```

Resend `brief`, `seats` and every earlier note character for character. A changed character makes
the earlier sittings play again with different results; the `expect` checkpoint turns that mistake
into an error instead.

If the user asks to end the debate early, go to step 5 with the sittings played so far.

## 5. Put the ballot and hold the vote

Build the ballot from the debate, not from your own view:

- 2 to 5 options with ids `A`, `B`, ..., each with a `title` of at most six words and a `summary` of
    at most 50 words in the council's own terms.
- Cover every distinct proposal still standing, every option the brief named, and the status quo if
    a member argued for it. Merge near-duplicates. Add nothing the council did not raise.
- A summary says what would be done under that option and nothing else: no arguments for or
    against it, and no word on who backs it or how the debate went.

Show the ballot to the user, then launch the vote with the same `sittings` and notes as the last
launch plus the ballot. You may append one last note for the final sitting if the council is still
owed a fact.

```
Workflow({
  name: "council:deliberation",
  resumeFromRunId: "<wf_...>",
  args: { brief, seats, sittings: <as before>, notes: [<as before>], expect: <checkpoint>, ballot: [{ id, title, summary }, ...] }
})
```

The vote is counted in code. `level` is the leading option's share of all seats: `unanimous`,
`consensus` (three quarters or more), `majority` (more than half) or `split`. A split triggers one
runoff between the two leading options: `runoff` is then true, `firstCount` holds the first count
and `count` the runoff. A runoff that is still split is final.

## 6. Report the verdict

Report in this order, in plain language:

1. **Outcome** - the winning option, the level and the count (and the first count if there was a
    runoff). On a `split`, present the two leading options evenly and hand the decision back.
2. **What the council recommends** - the concrete course of action.
3. **Why** - the two to four arguments that decided it, each attributed to its seat.
4. **Dissent** - the minority position, its strongest argument and who holds it. Never drop this.
5. **Who moved** - members whose vote differs from their opening (`changed_mind`) and the seat that
    moved them (`moved_by`).
6. **Participation** - who held the floor most and least, and any seat in `abstained`.
7. **What would change it** - the unknowns or facts that would flip the result.

Close with one line of candour: the council is one model speaking through sixteen lenses, so the
count shows how well an option holds up across perspectives, not how likely it is to be right. If
your own assessment differs from the council's, say so briefly under a separate heading; never
blend it into the verdict.

## When something fails

- **No Workflow tool:** dynamic workflows are off. Tell the user to enable them in `/config`, and
    do not act out the council yourself.
- **Error "resend them unchanged":** the brief or an earlier note changed. Launch again with the
    exact earlier text.
- **Error "nothing to resume":** the earlier run is gone. Tell the user and start a fresh debate.
- **Seats in `abstained`:** those members failed to answer. Report them, and count them as not
    having backed any option.

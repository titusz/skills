# Unstick — research the most stuck task

purpose: pick the single most stuck important task and contribute one genuinely useful piece of research or framing
mode: mutate
max-mutations: 1

## Gather

```bash
taskmate.py tasks --filter "priority >= 2 && updated < now-14d && done = false" --sort updated --order asc
```

Fetch `taskmate.py task <id>` for the top few — the comment trail tells you *why* each is
stuck: missing information, pending decision, unclear next step, or plain forgotten.

## Decide

Choose ONE task where an agent contribution plausibly unblocks it, preferring: blocks other
tasks > high priority > oldest stall. Skip any task the journal already shows an unstick
contribution for — a second research comment on a still-stuck task rarely helps; flag it in
the output as needing a human decision instead. Then match the contribution to the stall
type:

- **Missing information** → research it (web search/fetch; the `deep-research` skill if
    installed and warranted). Concrete facts, options, prices, deadlines, contacts — with
    sources.
- **Pending decision** → frame it: the 2–3 real options, one-line tradeoff each, and a
    recommendation with reasoning. (The `systems-thinking` skill helps when it's genuinely
    murky.)
- **Unclear next step** → propose the single smallest concrete next action.
- **Forgotten** → a respectful revival note: what it was, why it mattered, keep-or-kill
    question.

If no candidate would genuinely benefit — research can't help, or a human explicitly parked
it ("waiting for legal") — pick nothing.

## Act

With `--apply`: ONE comment on the chosen task — an insight up front, 1–3 supporting bullets,
sources when external research was used, and one suggested next action or decision question.
Companion mode signs it automatically; user mode requires the user's explicit go-ahead before
posting (interactively, show the draft first). Never change priority, owner, or due date here
— this playbook contributes context, not control.

## Output

The task, why it was chosen, and the contribution (or draft). Print `NO_ACTION` when nothing
qualified — a useless comment on a stuck task makes it *more* stuck, not less.
